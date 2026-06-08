"""Reusable pagination schemas."""

from pydantic import BaseModel


class Pagination(BaseModel):
    """Pagination metadata for list endpoints."""

    total: int
    page: int
    limit: int
    pages: int
