"""
Schemas for request and response bodies related to evaluations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from api.schemas.pagination import Pagination


class EvaluationStatusUpdate(BaseModel):
    """Schema for activating/deactivating an evaluation."""

    active: bool


class EvaluationOut(BaseModel):
    """Schema for outputting an evaluation."""

    id: int
    user_id: Optional[int]
    academic_period_id: Optional[int]
    academic_period_name: Optional[str]
    academic_period_code: Optional[str]
    department_id: Optional[int]
    pdf_url: Optional[str]
    active: Optional[bool]
    status: Optional[str]
    count: Optional[int]
    overall_average: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class EvaluationDetailResponse(BaseModel):
    """Schema for single evaluation response envelope."""

    status: int
    message: str
    data: Optional[EvaluationOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class EvaluationListResponse(BaseModel):
    """Schema for evaluations list response envelope."""

    status: int
    message: str
    data: list[EvaluationOut]
    error: Optional[str] = None
    timestamp: datetime
    pagination: Optional[Pagination] = None
    path: str
