"""
Schemas for request and response bodies related to programs.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class ProgramCreate(BaseModel):
    """Schema for creating a program."""

    name: str
    code: str


class ProgramUpdate(BaseModel):
    """Schema for updating a program."""

    name: Optional[str] = None
    code: Optional[str] = None
    active: Optional[bool] = None


class ProgramOut(BaseModel):
    """Schema for outputting a program."""

    id: int
    name: str
    code: str
    active: Optional[bool]
    created_at: datetime
    updated_at: datetime


@dataclass
class ProgramFilters:
    """Dataclass to hold program filters extracted from query parameters."""

    search: str | None = None
    active: bool | None = None


def program_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
) -> ProgramFilters:
    """Dependency function to extract program filters from query parameters."""

    return ProgramFilters(
        search=search,
        active=active,
    )


ProgramFiltersDep = Annotated[ProgramFilters, Depends(program_filters)]
