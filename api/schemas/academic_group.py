"""
Schemas for request and response bodies related to academic groups.
"""

from datetime import datetime
from typing import Optional

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


class AcademicGroupOut(BaseModel):
    """Schema for outputting an academic group."""

    id: int
    course_id: Optional[int]
    teacher_id: Optional[int]
    academic_period_id: Optional[int]
    group_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class AcademicGroupDetailResponse(BaseModel):
    """Schema for single academic group response envelope."""

    status: int
    message: str
    data: Optional[AcademicGroupOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class AcademicGroupListResponse(BaseModel):
    """Schema for academic groups list response envelope."""

    status: int
    message: str
    data: list[AcademicGroupOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
