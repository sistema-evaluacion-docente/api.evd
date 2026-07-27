"""WebSocket route for user notifications."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.core.websockets.connection_manager import connection_manager
from api.database import SessionLocal
from api.middlewares.auth import verify_token
from api.repositories.users import UsersRepository

logger = logging.getLogger(__name__)

router = APIRouter()


async def _authenticate_ws(token: str | None) -> dict | None:
    """Authenticate the WebSocket connection using the provided token."""

    if not token:
        return None
    try:
        decoded = verify_token(token)
        return decoded
    except Exception:
        return None


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str | None = None):
    """WebSocket endpoint for real-time user notifications."""

    decoded = await _authenticate_ws(token)

    if not decoded:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    uid = decoded.get("user_id")

    db = SessionLocal()
    try:
        users_repo = UsersRepository(db)
        user = users_repo.get_by_uid(uid)
        if not user:
            await websocket.close(code=4003, reason="User not found")
            return
        user_id = user.id
    finally:
        db.close()

    channel = f"notifications:{user_id}"

    await connection_manager.connect(websocket, channel)

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug("WS notifications received: %s", data)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        logger.info("Client disconnected from channel '%s'", channel)
    finally:
        await connection_manager.disconnect(websocket, channel)
