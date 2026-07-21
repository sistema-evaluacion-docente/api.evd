"""Middleware for collecting developer logs."""

import json
import re
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from api.config import config
from api.core.dev_logs.collector import dev_logs_collector

RECORD_ID_FROM_PATH = re.compile(r"/(\d+)(?:\?|$|/)")


class DevLogsMiddleware:
    """Middleware for collecting developer logs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Collect developer logs for HTTP requests and responses."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not config.DEBUG:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")

        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        if path.startswith("/ws"):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = {}

        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value

        status_code: int | None = None
        body_chunks: list[bytes] = []

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    body_chunks.append(body)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = (time.perf_counter() - start) * 1000

        path = path.rstrip("/") or "/"

        if status_code and 300 <= status_code < 400:
            return

        await dev_logs_collector.emit_request(
            method=method,
            path=path,
            query_params=query_params if query_params else None,
        )

        record_id = None
        detail = None

        path_match = RECORD_ID_FROM_PATH.search(path)
        if path_match:
            record_id = int(path_match.group(1))

        if body_chunks:
            raw_body = b"".join(body_chunks)
            try:
                parsed = json.loads(raw_body)
                if isinstance(parsed, dict):
                    if record_id is None and "id" in parsed:
                        record_id = parsed["id"]
                    detail = json.dumps(parsed, ensure_ascii=False)[:2000]
                elif isinstance(parsed, list):
                    detail = json.dumps(parsed, ensure_ascii=False)[:2000]
                else:
                    detail = str(parsed)[:2000]
            except (json.JSONDecodeError, UnicodeDecodeError):
                detail = raw_body.decode("utf-8", errors="replace")[:2000]

        await dev_logs_collector.emit_response(
            method=method,
            path=path,
            status_code=status_code or 500,
            duration_ms=duration_ms,
            record_id=record_id,
            detail=detail,
        )
