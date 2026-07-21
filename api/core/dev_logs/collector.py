"""
This module provides a DevLogsCollector class that collects and manages development logs.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from api.core.websockets.events import DevLogEvent

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = re.compile(
    r"(password|passwd|pwd|secret|token|api_key|apikey|authorization|"
    r"cookie|set-cookie|firebase|private_key|access_token|refresh_token|"
    r"hashed_password|hash|csrf)",
    re.IGNORECASE,
)

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "proxy-authorization",
}


def sanitize_value(key: str, value: Any) -> Any:
    """Sanitize sensitive keys by replacing their values with "***"."""

    if SENSITIVE_KEYS.search(str(key)):
        return "***"
    if isinstance(value, dict):
        return sanitize_dict(value)
    if isinstance(value, (list, tuple)):
        return [sanitize_value(key, item) for item in value]

    return value


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize sensitive keys in a dictionary by replacing their values with "***"."""

    return {k: sanitize_value(k, v) for k, v in data.items()}


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Sanitize sensitive headers by replacing their values
    with "***" if they are considered sensitive.
    """

    return {
        k: ("***" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()
    }


class DevLogsCollector:
    """A collector for development logs that allows subscribing to and emitting dev-log events."""

    MAX_SUBSCRIBERS = 100
    MAX_QUEUE_SIZE = 500

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._event_count = 0
        self._last_reset = datetime.now(timezone.utc)

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to dev-log events and return a queue for receiving them."""

        queue: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)

        async with self._lock:
            if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
                raise RuntimeError("Maximum dev-log subscribers reached")

            self._subscribers.append(queue)

        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe a queue from receiving dev-log events."""

        async with self._lock:
            try:
                self._subscribers.remove(queue)
            except ValueError:
                pass

    async def emit(self, event: DevLogEvent) -> None:
        """Emit a dev-log event to all subscribers."""

        async with self._lock:
            subscribers = list(self._subscribers)

        if not subscribers:
            return

        payload = event.model_dump_json()

        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Dev-log subscriber queue full, dropping event")

        self._event_count += 1

    async def emit_request(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
    ) -> None:
        """Emit a request event to all subscribers."""

        event = DevLogEvent(
            category="request",
            method=method,
            path=path,
            query_params=sanitize_dict(query_params) if query_params else None,
        )
        await self.emit(event)

    async def emit_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        record_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        """Emit a response event to all subscribers."""

        event = DevLogEvent(
            category="response",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            record_id=record_id,
            detail=detail,
        )

        await self.emit(event)

    async def emit_db_write(
        self,
        operation: str,
        model: str,
        record_id: int | None = None,
        details: dict | None = None,
    ) -> None:
        """Emit a database write event to all subscribers."""

        event = DevLogEvent(
            category="db_write",
            operation=operation,
            model=model,
            record_id=record_id,
            details=sanitize_dict(details) if details else None,
        )

        await self.emit(event)

    @property
    def subscriber_count(self) -> int:
        """Return the current number of subscribers."""

        return len(self._subscribers)


dev_logs_collector = DevLogsCollector()
