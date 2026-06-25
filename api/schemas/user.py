"""
Schemas for request and response bodies related to users.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from api.schemas.pagination import Pagination


class RoleName(str, Enum):
    """Allowed role names in the system."""

    DOCENTE = "DOCENTE"
    DIRECTOR_DE_DEPARTAMENTO = "DIRECTOR DE DEPARTAMENTO"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    """

    uid: Optional[str] = None
    email: str
    username: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = True
    avatar_url: Optional[str] = None
    institutional_code: Optional[str] = None
    contract_type: Optional[str] = None
    roles: list[RoleName] = Field(
        default_factory=lambda: [RoleName.DOCENTE],
        min_length=1,
    )


class UserUpdate(BaseModel):
    """
    Schema for updating a user.
    """

    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None
    avatar_url: Optional[str] = None
    roles: Optional[list[RoleName]] = Field(default=None, min_length=1)


class UserOut(BaseModel):
    """
    Schema for outputting a user.
    """

    id: int
    uid: Optional[str]
    email: str
    username: Optional[str]
    name: Optional[str]
    department_id: Optional[int]
    active: Optional[bool]
    avatar_url: Optional[str]
    roles: list[RoleName]

    created_at: datetime
    updated_at: datetime


class UserRolesUpdate(BaseModel):
    """Schema for replacing all roles assigned to a user."""

    roles: list[RoleName] = Field(min_length=1)


class UserStatusUpdate(BaseModel):
    """Schema for activating/deactivating a user."""

    active: bool


class UserRolesOut(BaseModel):
    """Schema for roles assigned to a user."""

    id: int
    uid: Optional[str]
    roles: list[RoleName]


class TokenUser(BaseModel):
    """
    Schema for the current user.
    """

    uid: str
    email: str
    name: str
    picture: str


class UserDetailResponse(BaseModel):
    """Schema for user endpoint response envelopes."""

    status: int
    message: str
    data: Optional[UserOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class UserListResponse(BaseModel):
    """Schema for users list endpoint response envelopes."""

    status: int
    message: str
    data: list[UserOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str
