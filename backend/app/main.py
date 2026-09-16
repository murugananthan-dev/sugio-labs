import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .api.routes import router as api_router
from .api.websocket import ws_manager
from .agents.supervisor import agent_supervisor
from .permissions.manager import permission_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sugio_labs")


def _frontend_dist_dir() -> Path:
    """Return the bundled frontend directory for source and PyInstaller builds."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "frontend_dist"
    return Path(__file__).resolve().parents[1] / "frontend_dist"


FRONTEND_DIST = _frontend_dist_dir()
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and teardown events."""
    logger.info("Initializing Sugio Labs Backend Engine...")

    # Wire up WebSocket callbacks
    agent_supervisor.set_ws_broadcast(ws_manager.broadcast)
    permission_manager.register_broadcast_callback(ws_manager.broadcast_permission_request)

    logger.info(f"Sugio Labs Backend initialized on http://{settings.host}:{settings.port}")
    yield
    logger.info("Shutting down Sugio Labs Backend Engine...")


app = FastAPI(
    title=settings.app_name,
    description="Local, Human-Controlled AI Software Development Agent Backend",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS for development and local desktop hosting.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST Routers
app.include_router(api_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket endpoint for event streaming and permission alerts."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received WS message: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        ws_manager.disconnect(websocket)


# In desktop builds the Vite output is copied into backend/frontend_dist and
# bundled by PyInstaller. Mount hashed Vite assets before the SPA fallback.
if (FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="frontend-assets",
    )


@app.get("/", include_in_schema=False)
async def root():
    """Serve the desktop/web UI when bundled, otherwise expose API metadata."""
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return JSONResponse(
        {
            "name": settings.app_name,
            "status": "online",
            "docs_url": "/docs",
            "api_prefix": "/api/v1",
        }
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_fallback(full_path: str):
    """Serve static frontend files and fall back to index.html for the SPA."""
    if FRONTEND_INDEX.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            return FileResponse(FRONTEND_INDEX)

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)

    return JSONResponse({"detail": "Not Found"}, status_code=404)
