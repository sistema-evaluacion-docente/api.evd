"""
Schemas for request and response bodies related to teachers.
"""

from datetime import datetime
from typing import Optional

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
        v = v.strip()

        if not v.isdigit():
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
    created_at: datetime
    updated_at: datetime


class TeacherDetailResponse(BaseModel):
    """Schema for single teacher response envelope."""

    status: int
    message: str
    data: Optional[TeacherOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class TeacherListResponse(BaseModel):
    """Schema for teachers list response envelope."""

    status: int
    message: str
    data: list[TeacherOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str


class BulkUploadResult(BaseModel):
    """Schema for bulk upload result."""

    created: list[dict]
    skipped: list[dict]
    errors: list[dict]


class TeacherBulkUploadResponse(BaseModel):
    """Schema for bulk upload response envelope."""

    status: int
    message: str
    data: BulkUploadResult
    error: Optional[str] = None
    timestamp: datetime
    path: str
