"""Schemas for Director entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field


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
    username: Optional[str] = None
    uid: Optional[str] = None
    avatar_url: Optional[str] = None
    institutional_code: Optional[str] = None
    contract_type: Optional[str] = None
    department_id: int
    roles: list[str] = Field(default=["DIRECTOR_DE_DEPARTAMENTO"])


class DirectorUpdate(BaseModel):
    """Schema for updating a director."""

    user_id: Optional[int] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None


class DirectorOut(BaseModel):
    """Schema for outputting director information with nested user and department summaries."""

    id: int
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
