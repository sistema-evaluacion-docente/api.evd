"""
Schemas for request and response bodies related to departments.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class DirectorSummary(BaseModel):
    """Lightweight director info embedded in DepartmentOut."""

    id: int
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class DepartmentCreate(BaseModel):
    """Schema for creating a department."""

    code: str
    name: str
    faculty_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    """Schema for updating a department."""

    code: Optional[str] = None
    name: Optional[str] = None
    faculty_id: Optional[int] = None
    active: Optional[bool] = None


class AssignDirectorRequest(BaseModel):
    """Schema for assigning a director to a department."""

    user_id: int


class DepartmentOut(BaseModel):
    """Schema for outputting a department."""

    id: int
    code: str
    name: str
    faculty_id: Optional[int]
    active: Optional[bool]
    director: Optional[DirectorSummary] = None
    teacher_count: int = 0
    created_at: datetime
    updated_at: datetime


@dataclass
class DepartmentFilters:
    """Dataclass to hold department filters extracted from query parameters."""

    search: str | None = None
    active: bool | None = None
    faculty_id: int | None = None


def department_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
    faculty_id: int | None = Query(default=None),
) -> DepartmentFilters:
    """Dependency function to extract department filters from query parameters."""

    return DepartmentFilters(
        search=search,
        active=active,
        faculty_id=faculty_id,
    )


DepartmentFiltersDep = Annotated[DepartmentFilters, Depends(department_filters)]
