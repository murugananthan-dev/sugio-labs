import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for React Vite Frontend (localhost:5173 / localhost:3000)
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
            # Echo or process client events
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "status": "online",
        "docs_url": "/docs",
        "api_prefix": "/api/v1",
    }
