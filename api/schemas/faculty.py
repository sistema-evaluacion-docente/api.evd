"""
Schemas for request and response bodies related to faculties.
"""

from datetime import datetime
from typing import Optional

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
    created_at: datetime
    updated_at: datetime


class FacultyDetailResponse(BaseModel):
    """Schema for single faculty response envelope."""

    status: int
    message: str
    data: Optional[FacultyOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class FacultyListResponse(BaseModel):
    """Schema for faculties list response envelope."""

    status: int
    message: str
    data: list[FacultyOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
