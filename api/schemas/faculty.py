"""
Schemas for request and response bodies related to faculties.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class FacultyCreate(BaseModel):
    """Schema for creating a faculty."""

    name: str
    code: str


class FacultyUpdate(BaseModel):
    """Schema for updating a faculty."""

    name: Optional[str] = None
    code: Optional[str] = None
    active: Optional[bool] = None


class FacultyOut(BaseModel):
    """Schema for outputting a faculty."""

    id: int
    name: str
    code: str
    active: Optional[bool]
    department_count: int = 0
    created_at: datetime
    updated_at: datetime


@dataclass
class FacultyFilters:
    """Dataclass to hold faculty filters extracted from query parameters."""

    search: str | None = None
    active: bool | None = None


def faculty_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
) -> FacultyFilters:
    """Dependency function to extract faculty filters from query parameters."""

    return FacultyFilters(
        search=search,
        active=active,
    )


FacultyFiltersDep = Annotated[FacultyFilters, Depends(faculty_filters)]
