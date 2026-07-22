"""
Schemas for request and response bodies related to teachers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, field_validator

from api.schemas.user import UserOut


class TeacherCreate(BaseModel):
    """Schema for creating a teacher."""

    institutional_code: str
    department_id: Optional[int] = None
    contract_type: Optional[str] = None
    user_id: Optional[int] = None

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


class TeacherCreateWithUser(BaseModel):
    """Schema for creating a teacher with user information."""

    email: str
    name: str
    institutional_code: str
    department_id: Optional[int] = None
    contract_type: Optional[str] = None
    active: Optional[bool] = True

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


class TeacherUpdate(BaseModel):
    """Schema for updating a teacher."""

    institutional_code: Optional[str] = None
    department_id: Optional[int] = None
    contract_type: Optional[str] = None
    user_id: Optional[int] = None
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


class TeacherOut(BaseModel):
    """Schema for outputting a teacher."""

    id: int
    institutional_code: str
    department_id: Optional[int]
    contract_type: Optional[str]
    user_id: Optional[int]
    user: Optional[UserOut] = None
    active: Optional[bool]
    overall_average: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class BulkUploadResult(BaseModel):
    """Schema for bulk upload result."""

    created: list[dict]
    skipped: list[dict]
    errors: list[dict]


@dataclass
class TeacherFilters:
    """Dataclass to hold teacher filters extracted from query parameters."""

    search: str | None = None
    active: bool | None = None
    department_id: int | None = None
    contract_type: str | None = None


def teacher_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
    department_id: int | None = Query(default=None),
    contract_type: str | None = Query(default=None),
) -> TeacherFilters:
    """Dependency function to extract teacher filters from query parameters."""

    return TeacherFilters(
        search=search,
        active=active,
        department_id=department_id,
        contract_type=contract_type,
    )


TeacherFiltersDep = Annotated[TeacherFilters, Depends(teacher_filters)]
