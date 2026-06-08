"""
Schemas for request and response bodies related to users.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RoleName(str, Enum):
    """Allowed role names in the system."""

    DOCETE = "DOCETE"
    DIRECTOR_DE_DEPARTAMENTO = "DIRECTOR DE DEPARTAMENTO"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    """

    uid: str
    email: str
    username: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = True
    avatar_url: Optional[str] = None
    roles: list[RoleName] = Field(
        default_factory=lambda: [RoleName.DOCETE],
        min_length=1,
    )


class UserUpdate(BaseModel):
    """
    Schema for updating a user.
    """

    email: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None
    avatar_url: Optional[str] = None
    roles: Optional[list[RoleName]] = Field(default=None, min_length=1)


class UserOut(BaseModel):
    """
    Schema for outputting a user.
    """

    uid: str
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


class UserRolesOut(BaseModel):
    """Schema for roles assigned to a user."""

    uid: str
    roles: list[RoleName]


class TokenUser(BaseModel):
    """
    Schema for the current user.
    """

    uid: str
    email: str
    name: str
    picture: str
