"""
Schemas for request and response bodies related to users.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field


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
    department_id: Optional[int]
    name: Optional[str]
    active: Optional[bool]
    avatar_url: Optional[str]
    roles: list[RoleName]
    teacher_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class UserRolesUpdate(BaseModel):
    """Schema for replacing all roles assigned to a user."""

    roles: list[RoleName] = Field(min_length=1)


class UserStatusUpdate(BaseModel):
    """Schema for activating/deactivating a user."""

    active: bool


class TokenUser(BaseModel):
    """
    Schema for the current user.
    """

    uid: str
    email: str
    name: str
    picture: str


@dataclass
class UserFilters:
    """
    Dataclass to hold user filters extracted from query parameters.
    """

    search: str | None = None
    active: bool | None = None


def user_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
) -> UserFilters:
    """
    Dependency function to extract user filters from query parameters.
    """

    return UserFilters(search=search, active=active)


UserFiltersDep = Annotated[UserFilters, Depends(user_filters)]
