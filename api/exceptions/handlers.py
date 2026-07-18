"""
Exception handlers for the application.
"""

from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import config
from api.exceptions import AppException


def build_error_envelope(
    code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
) -> dict:
    """Build a standard error envelope."""

    envelope = {
        "status": "error",
        "data": None,
        "pagination": None,
        "error": {
            "code": code,
            "message": message,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if details:
        envelope["error"]["details"] = details

    return envelope


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom AppException."""

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors (422)."""

    errors = []

    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"]) if error["loc"] else ""

        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"errors": errors},
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTPException from FastAPI."""

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", exc.detail.get("detail", str(exc.detail)))
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=code,
            message=message,
            status_code=exc.status_code,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions (500)."""

    if config.DEBUG:
        message = str(exc)
        details = {"type": type(exc).__name__}
    else:
        message = "An internal error occurred"
        details = None

    return JSONResponse(
        status_code=500,
        content=build_error_envelope(
            code="INTERNAL_SERVER_ERROR",
            message=message,
            status_code=500,
            details=details,
        ),
    )
