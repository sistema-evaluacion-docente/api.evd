"""Reusable pagination schemas."""

from math import ceil

from pydantic import BaseModel


class Pagination(BaseModel):
    """Pagination metadata for list endpoints."""

    total: int
    page: int
    limit: int
    pages: int


def build_paginated_response(items: list, total: int, pagination) -> dict:
    """Build a paginated response with metadata."""

    pages = ceil(total / pagination.limit) if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "limit": pagination.limit,
        "pages": pages,
    }
