import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from ..models.schemas import WSMessage, PermissionRequest, WSMessageType

logger = logging.getLogger("sugio_labs.api.websocket")


class ConnectionManager:
    """Manages active WebSocket connections from React frontend clients."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: WSMessage):
        """Broadcasts a structured WSMessage to all connected WebSocket clients."""
        payload_json = message.model_dump(mode="json")
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(payload_json)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                disconnected_clients.append(connection)

        for conn in disconnected_clients:
            self.disconnect(conn)

    async def broadcast_permission_request(self, req: PermissionRequest):
        """Specialized helper to broadcast permission requests to UI."""
        msg = WSMessage(
            type=WSMessageType.PERMISSION_REQUIRED,
            payload=req.model_dump(mode="json"),
        )
        await self.broadcast(msg)


ws_manager = ConnectionManager()
