"""
Schemas for request and response bodies related to users.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field, field_validator


class RoleName(str, Enum):
    """Allowed role names in the system."""

    DOCENTE = "DOCENTE"
    DIRECTOR_DE_DEPARTAMENTO = "DIRECTOR DE DEPARTAMENTO"
    ADMIN = "ADMIN"
    DECANO = "DECANO"
    VICERRECTOR_ACADEMICO = "VICERRECTOR ACADEMICO"


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    """

    uid: Optional[str] = None
    email: str
    name: Optional[str] = None
    active: Optional[bool] = True
    avatar_url: Optional[str] = None
    institutional_code: Optional[str] = None
    contract_type: Optional[str] = None
    department_id: Optional[int] = None
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


class UserAdminUpdate(BaseModel):
    """Schema for an administrator editing any user.

    ``department_id`` is the teacher record's department, so it only applies to
    a user who ends up with the DOCENTE role; sending it as ``null`` clears it.
    Director and dean assignments keep their own endpoints.
    """

    name: Optional[str] = None
    email: Optional[str] = None
    institutional_code: Optional[str] = None
    roles: Optional[list[RoleName]] = Field(default=None, min_length=1)
    department_id: Optional[int] = None
    active: Optional[bool] = None

    @field_validator("active")
    @classmethod
    def validate_active(cls, v: Optional[bool]) -> bool:
        """Reject an explicit null: a user is either active or not."""

        if v is None:
            raise ValueError("active no puede ser nulo")

        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> str:
        """Reject a blank or null name."""

        if v is None or not v.strip():
            raise ValueError("El nombre no puede estar vacío")

        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> str:
        """Normalize the email the way Firebase reports it on login."""

        if v is None or not v.strip():
            raise ValueError("El correo no puede estar vacío")

        v = v.strip().lower()

        if "@" not in v:
            raise ValueError("El correo no es válido")

        return v

    @field_validator("institutional_code")
    @classmethod
    def validate_institutional_code(cls, v: Optional[str]) -> str:
        """Same rule as teachers: an integer without decimals."""

        if v is None or not v.strip().isdigit():
            raise ValueError(
                "institutional_code debe ser un número entero sin decimales"
            )

        return v.strip()


class UserSelfUpdate(BaseModel):
    """Schema for the fields a user may change on their own account.

    Deliberately narrower than ``UserUpdate``: it carries neither ``roles`` nor
    ``active``. Both decide what the account is allowed to do, so they belong to
    an administrator and travel through ``PUT /users/{uid}/roles`` and
    ``PATCH /users/{uid}/status``. Accepting them here let any authenticated
    user grant themselves ADMIN.
    """

    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserOut(BaseModel):
    """
    Schema for outputting a user.
    """

    id: int
    uid: Optional[str]
    email: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    name: Optional[str]
    active: Optional[bool]
    avatar_url: Optional[str]
    institutional_code: Optional[str] = None
    roles: list[RoleName]
    teacher_id: Optional[int] = None
    # Department of the user's teacher record. department_id above is resolved
    # by role, so for a director it is the department they direct, which can
    # differ from this one.
    teacher_department_id: Optional[int] = None
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
    roles: Optional[list[RoleName]] = None
    department_id: int | None = None


def user_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
    roles: Optional[list[RoleName]] = Query(default=None),
    department_id: int | None = Query(
        default=None,
        description=(
            "Usuarios del departamento: los que tienen allí su registro de "
            "docente o son su director."
        ),
    ),
) -> UserFilters:
    """
    Dependency function to extract user filters from query parameters.
    """

    return UserFilters(
        search=search, active=active, roles=roles, department_id=department_id
    )


UserFiltersDep = Annotated[UserFilters, Depends(user_filters)]
