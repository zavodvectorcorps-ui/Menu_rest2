import logging
from fastapi import WebSocket
from typing import Dict, List
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per restaurant."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, restaurant_id: str):
        await websocket.accept()
        if restaurant_id not in self.active_connections:
            self.active_connections[restaurant_id] = []
        self.active_connections[restaurant_id].append(websocket)
        logger.info(f"WS connected: restaurant={restaurant_id}, total={len(self.active_connections[restaurant_id])}")

    def disconnect(self, websocket: WebSocket, restaurant_id: str):
        if restaurant_id in self.active_connections:
            self.active_connections[restaurant_id] = [
                ws for ws in self.active_connections[restaurant_id] if ws != websocket
            ]
            if not self.active_connections[restaurant_id]:
                del self.active_connections[restaurant_id]
        logger.info(f"WS disconnected: restaurant={restaurant_id}")

    async def broadcast(self, restaurant_id: str, event_type: str, data: dict):
        if restaurant_id not in self.active_connections:
            return
        
        message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False, default=str)
        dead_connections = []
        
        for ws in self.active_connections[restaurant_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)
        
        for ws in dead_connections:
            self.disconnect(ws, restaurant_id)


manager = ConnectionManager()
