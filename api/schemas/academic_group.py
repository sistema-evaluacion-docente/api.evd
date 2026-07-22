"""
Schemas for request and response bodies related to academic groups.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class AcademicGroupCreate(BaseModel):
    """Schema for creating an academic group."""

    course_id: int
    teacher_id: int
    academic_period_id: int
    group_name: Optional[str] = None


class AcademicGroupUpdate(BaseModel):
    """Schema for updating an academic group."""

    course_id: Optional[int] = None
    teacher_id: Optional[int] = None
    academic_period_id: Optional[int] = None
    group_name: Optional[str] = None


class CourseSummary(BaseModel):
    """Lightweight nested schema for the group's course."""

    id: int
    code: str
    name: Optional[str]
    department_id: Optional[int]


class TeacherSummary(BaseModel):
    """Lightweight nested schema for the group's teacher."""

    id: int
    institutional_code: str
    name: Optional[str] = None


class AcademicPeriodSummary(BaseModel):
    """Lightweight nested schema for the group's academic period."""

    id: int
    code: str
    name: Optional[str]
    active: Optional[bool]


class AcademicGroupOut(BaseModel):
    """Schema for outputting an academic group."""

    id: int
    course_id: Optional[int]
    teacher_id: Optional[int]
    academic_period_id: Optional[int]
    group_name: Optional[str]
    course: Optional[CourseSummary] = None
    teacher: Optional[TeacherSummary] = None
    academic_period: Optional[AcademicPeriodSummary] = None
    created_at: datetime
    updated_at: datetime


@dataclass
class AcademicGroupFilters:
    """Dataclass to hold academic group filters extracted from query parameters."""

    search: str | None = None
    course_id: int | None = None
    teacher_id: int | None = None
    academic_period_id: int | None = None
    department_id: int | None = None


def academic_group_filters(
    search: str | None = Query(default=None, min_length=1),
    course_id: int | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    academic_period_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
) -> AcademicGroupFilters:
    """Dependency function to extract academic group filters from query parameters."""

    return AcademicGroupFilters(
        search=search,
        course_id=course_id,
        teacher_id=teacher_id,
        academic_period_id=academic_period_id,
        department_id=department_id,
    )


AcademicGroupFiltersDep = Annotated[
    AcademicGroupFilters, Depends(academic_group_filters)
]
