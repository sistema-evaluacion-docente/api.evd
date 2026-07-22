"""
Response envelope middleware.
"""

import json
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

EXCLUDED_PATHS = {"/docs", "/redoc", "/openapi.json"}
EXCLUDED_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/uploads")
PAGINATION_KEYS = {"total", "page", "limit", "pages"}


def build_success_envelope(
    data: Any,
    status_code: int,
    pagination: dict | None = None,
) -> dict:
    """Build a standard success envelope."""

    return {
        "status": "success",
        "data": data,
        "pagination": pagination,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def extract_pagination(body: dict) -> tuple[Any, dict | None]:
    """
    Extract pagination metadata from response body if present.

    Returns (data, pagination) where:
    - If body contains all pagination keys (total, page, limit, pages),
      they are extracted and the remaining body becomes data.
    - Otherwise, the full body is data and pagination is None.
    """

    if not isinstance(body, dict):
        return body, None

    body_keys = set(body.keys())
    if not PAGINATION_KEYS.issubset(body_keys):
        return body, None

    pagination = {
        "total": body["total"],
        "page": body["page"],
        "limit": body["limit"],
        "pages": body["pages"],
    }

    remaining = {k: v for k, v in body.items() if k not in PAGINATION_KEYS}

    if len(remaining) == 1 and "items" in remaining:
        data = remaining["items"]
    elif not remaining:
        data = None
    else:
        data = remaining

    return data, pagination


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """
    Middleware that wraps all JSON responses in a standard envelope format.

    Success responses (status < 400):
    {
        "status": "success",
        "data": <original body>,
        "pagination": {"total": int, "page": int, "limit": int, "pages": int} | null,
        "error": null,
        "timestamp": "<ISO 8601 UTC>"
    }

    If the response body contains all pagination keys (total, page, limit, pages),
    they are automatically extracted into the pagination field.

    Excludes: /docs, /redoc, /openapi.json, and non-JSON responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if self._should_skip(request, response):
            return response

        if isinstance(response, StreamingResponse):
            return response

        if response.status_code >= 400:
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body_chunks = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body = b"".join(body_chunks)

        try:
            original_data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

        data, pagination = extract_pagination(original_data)
        envelope = build_success_envelope(data, response.status_code, pagination)
        envelope_bytes = json.dumps(envelope, default=str).encode("utf-8")

        return Response(
            content=envelope_bytes,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "content-length": str(len(envelope_bytes)),
            },
            media_type="application/json",
        )

    @staticmethod
    def _should_skip(request: Request, response: Response) -> bool:
        path = request.url.path

        if path in EXCLUDED_PATHS:
            return True

        for prefix in EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return True

        if isinstance(response, StreamingResponse):
            return True

        return False
