"""Connection manager for WebSocket connections."""

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

from api.core.websockets.events import BaseWebSocketEvent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and channels."""

    def __init__(self):
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accepts a WebSocket connection and adds it to the specified channel."""

        await websocket.accept()
        async with self._lock:
            self._channels[channel].add(websocket)
        logger.debug(
            "WS connected to channel '%s' (%d total)",
            channel,
            len(self._channels[channel]),
        )

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Removes a WebSocket connection from the specified channel."""

        async with self._lock:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
        logger.debug("WS disconnected from channel '%s'", channel)

    async def broadcast(self, channel: str, event: BaseWebSocketEvent) -> None:
        """Broadcasts an event to all WebSocket connections in the specified channel."""

        async with self._lock:
            connections = set(self._channels.get(channel, set()))

        if not connections:
            return

        payload = event.model_dump_json()
        stale: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._channels[channel].discard(ws)

    def channel_count(self, channel: str) -> int:
        """Returns the number of active WebSocket connections in the specified channel."""

        return len(self._channels.get(channel, set()))

    @property
    def active_channels(self) -> list[str]:
        """Returns a list of active channel names."""

        return list(self._channels.keys())


connection_manager = ConnectionManager()
