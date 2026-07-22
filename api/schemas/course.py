"""
Schemas for request and response bodies related to courses.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class DepartmentSummary(BaseModel):
    """Lightweight nested schema for the course's department."""

    id: int
    code: str
    name: str


class CourseCreate(BaseModel):
    """Schema for creating a course."""

    code: str
    name: Optional[str] = None
    department_id: Optional[int] = None


class CourseUpdate(BaseModel):
    """Schema for updating a course."""

    code: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None


class CourseOut(BaseModel):
    """Schema for outputting a course."""

    id: int
    code: str
    name: Optional[str]
    department_id: Optional[int]
    department: Optional[DepartmentSummary] = None
    created_at: datetime
    updated_at: datetime


@dataclass
class CourseFilters:
    """Dataclass to hold course filters extracted from query parameters."""

    search: str | None = None
    department_id: int | None = None


def course_filters(
    search: str | None = Query(default=None, min_length=1),
    department_id: int | None = Query(default=None),
) -> CourseFilters:
    """Dependency function to extract course filters from query parameters."""

    return CourseFilters(
        search=search,
        department_id=department_id,
    )


CourseFiltersDep = Annotated[CourseFilters, Depends(course_filters)]
