"""
Schemas for request and response bodies related to evaluations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EvaluationOut(BaseModel):
    """Schema for outputting an evaluation."""

    id: int
    user_id: Optional[str]
    academic_period_id: Optional[int]
    department_id: Optional[int]
    pdf_url: Optional[str]
    status: Optional[str]
    count: Optional[int]
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
    path: str
