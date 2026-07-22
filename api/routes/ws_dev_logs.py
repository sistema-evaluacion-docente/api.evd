"""WebSocket route for development logs."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.config import config
from api.core.dev_logs.collector import dev_logs_collector

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasting messages to connected clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts a new WebSocket connection and adds it to the list of active connections."""

        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Removes a WebSocket connection from the list of active connections."""

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Sends a message to all active WebSocket connections."""

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass


manager = ConnectionManager()


async def send_updates(websocket: WebSocket):
    """Background task to send updates to the connected WebSocket client."""

    queue = await dev_logs_collector.subscribe()

    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_text(payload)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        print("Background sender task was cancelled cleanly.")
    finally:
        await dev_logs_collector.unsubscribe(queue)


@router.websocket("/ws/devlogs")
async def ws_dev_logs(websocket: WebSocket):
    """WebSocket endpoint for streaming development logs to authenticated admin users."""

    if not config.DEBUG:
        logger.info("DEBUG mode is disabled, rejecting connection")

        await websocket.close(
            code=1008, reason="Dev logs only available in development"
        )

        return

    await manager.connect(websocket)

    sender_task = asyncio.create_task(send_updates(websocket))

    try:
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received: {data}")
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        print("Client disconnected.")
    finally:
        manager.disconnect(websocket)
        sender_task.cancel()
        await asyncio.gather(sender_task, return_exceptions=True)
