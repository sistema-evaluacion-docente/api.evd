"""
Schemas for request and response bodies related to directors.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from api.schemas.pagination import Pagination
from api.schemas.user import RoleName


class DirectorCreate(BaseModel):
    """Schema for creating a director."""

    email: str
    name: Optional[str] = None
    username: Optional[str] = None
    uid: Optional[str] = None
    avatar_url: Optional[str] = None
    institutional_code: Optional[str] = None
    contract_type: Optional[str] = None
    department_id: int
    roles: list[RoleName] = Field(
        default_factory=lambda: [RoleName.DIRECTOR_DE_DEPARTAMENTO],
        min_length=1,
    )


class DirectorRecordCreate(BaseModel):
    """Internal schema for creating a director record."""

    user_id: int
    department_id: int


class DirectorUpdate(BaseModel):
    """Schema for updating a director."""

    user_id: Optional[int] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None


class DirectorOut(BaseModel):
    """Schema for outputting a director."""

    id: int
    user_id: int
    department_id: int
    user: Optional[dict] = None
    department: Optional[dict] = None
    active: Optional[bool]
    created_at: datetime
    updated_at: datetime


class DirectorDetailResponse(BaseModel):
    """Schema for single director response envelope."""

    status: int
    message: str
    data: Optional[DirectorOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class DirectorListResponse(BaseModel):
    """Schema for directors list response envelope."""

    status: int
    message: str
    data: list[DirectorOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str
