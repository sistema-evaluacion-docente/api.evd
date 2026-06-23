"""
Schemas for request and response bodies related to courses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CourseCreate(BaseModel):
    """Schema for creating a course."""

    code: str
    name: Optional[str] = None
    department_id: Optional[int] = None


class CourseUpdate(BaseModel):
    """Schema for updating a course."""

    name: Optional[str] = None
    department_id: Optional[int] = None


class CourseOut(BaseModel):
    """Schema for outputting a course."""

    id: int
    code: str
    name: Optional[str]
    department_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(BaseModel):
    """Schema for single course response envelope."""

    status: int
    message: str
    data: Optional[CourseOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class CourseListResponse(BaseModel):
    """Schema for courses list response envelope."""

    status: int
    message: str
    data: list[CourseOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
