"""WebSocket route for development logs."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.config import config
from api.core.dev_logs.collector import dev_logs_collector

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/devlogs")
async def ws_dev_logs(websocket: WebSocket):
    """WebSocket endpoint for streaming development logs to authenticated admin users."""

    if not config.DEBUG:
        logger.info("DEBUG mode is disabled, rejecting connection")

        await websocket.close(
            code=1008, reason="Dev logs only available in development"
        )

        return

    await websocket.accept()

    queue = await dev_logs_collector.subscribe()

    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_text(payload)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await dev_logs_collector.unsubscribe(queue)
