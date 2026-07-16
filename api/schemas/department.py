"""
Schemas for request and response bodies related to departments.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from api.schemas.pagination import Pagination


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
    director: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class DepartmentDetailResponse(BaseModel):
    """Schema for single department response envelope."""

    status: int
    message: str
    data: Optional[DepartmentOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class DepartmentListResponse(BaseModel):
    """Schema for departments list response envelope."""

    status: int
    message: str
    data: list[DepartmentOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str
