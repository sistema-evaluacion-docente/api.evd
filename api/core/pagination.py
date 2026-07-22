"""
Pagination utilities for the API.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


@dataclass
class PaginationParams:
    """Class to hold pagination parameters."""

    page: int
    limit: int

    @property
    def offset(self) -> int:
        """Calculate the offset based on the current page and limit."""

        return (self.page - 1) * self.limit


def pagination_params(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
) -> PaginationParams:
    """Dependency to extract pagination parameters from query parameters."""

    return PaginationParams(page=page, limit=limit)


PaginationDep = Annotated[PaginationParams, Depends(pagination_params)]
