from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from api.schemas.pagination import Pagination


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
