"""Schemas for Director entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field, field_validator


class UserSummary(BaseModel):
    """Summary of user for nesting in DirectorOut."""

    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class DepartmentSummary(BaseModel):
    """Summary of department for nesting in DirectorOut."""

    id: int
    name: str
    code: str


class DirectorCreate(BaseModel):
    """Schema for creating a director with user and department information."""

    email: str
    name: Optional[str] = None
    uid: Optional[str] = None
    avatar_url: Optional[str] = None
    institutional_code: str
    contract_type: Optional[str] = None
    department_id: int
    roles: list[str] = Field(default=["DIRECTOR_DE_DEPARTAMENTO"])

    @field_validator("institutional_code")
    @classmethod
    def validate_institutional_code(cls, v: str) -> str:
        """Validate that the institutional_code is a string representing an integer without decimals."""

        v = v.strip()

        if not v.isdigit():
            raise ValueError(
                "institutional_code debe ser un número entero sin decimales"
            )

        return v


class DirectorUpdate(BaseModel):
    """Schema for updating a director."""

    institutional_code: Optional[str] = None
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None

    @field_validator("institutional_code")
    @classmethod
    def validate_institutional_code(cls, v: str) -> str:
        """Validate that the institutional_code is a string representing an integer without decimals."""

        v = v.strip()

        if v is not None and not v.isdigit():
            raise ValueError(
                "institutional_code debe ser un número entero sin decimales"
            )

        return v


class DirectorOut(BaseModel):
    """Schema for outputting director information with nested user and department summaries."""

    id: int
    institutional_code: str
    user_id: int
    department_id: int
    user: Optional[UserSummary] = None
    department: Optional[DepartmentSummary] = None
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class DirectorFilters:
    """Filters for searching directors."""

    search: Optional[str] = None
    active: Optional[bool] = None


def director_filters(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
) -> DirectorFilters:
    """Create DirectorFilters from query parameters."""

    return DirectorFilters(search=search, active=active)


DirectorFiltersDep = Annotated[DirectorFilters, Depends(director_filters)]
