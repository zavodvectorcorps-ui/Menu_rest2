from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
import os
import logging

from database import db
from models import UserRole
from services.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()

SECRET_KEY = os.environ.get('JWT_SECRET')
ALGORITHM = "HS256"


async def authenticate_ws(token: str) -> dict:
    """Verify JWT token for WebSocket connection."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user or not user.get("is_active", True):
            return None
        return user
    except JWTError:
        return None


@router.websocket("/ws/{restaurant_id}")
async def websocket_endpoint(websocket: WebSocket, restaurant_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    user = await authenticate_ws(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    if user.get("role") != UserRole.SUPERADMIN and restaurant_id not in user.get("restaurant_ids", []):
        await websocket.close(code=4003, reason="Access denied")
        return

    await manager.connect(websocket, restaurant_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id)
    except Exception:
        manager.disconnect(websocket, restaurant_id)
