"""Response schemas for the API."""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from api.schemas.pagination import Pagination

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        None, description="Additional error details (only in DEBUG mode for 500 errors)"
    )


class ResponseEnvelope(BaseModel, Generic[T]):
    """
    Generic response envelope for all API responses.
    """

    status: str = Field(
        ...,
        description="Response status: 'success' or 'error'",
        examples=["success", "error"],
    )
    data: T | None = Field(
        None,
        description="Response payload (null for error responses)",
    )
    pagination: Pagination | None = Field(
        None,
        description="Pagination metadata (only for paginated list endpoints)",
    )
    error: ErrorDetail | None = Field(
        None,
        description="Error details (null for success responses)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp of the response",
    )


class ResponseSchema(BaseModel):
    """Standard API response envelope."""

    status: int
    message: str
    data: Any | None = None
    pagination: Pagination | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    path: str


class HealthResponseSchema(BaseModel):
    """Health-check response schema."""

    status: str
