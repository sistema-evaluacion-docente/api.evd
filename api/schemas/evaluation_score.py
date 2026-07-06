"""
Schemas for request and response bodies related to evaluation scores.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class EvaluationScoreOut(BaseModel):
    """Schema for outputting an evaluation score."""

    id: int
    evaluation_id: int
    academic_group_id: int
    group_name: Optional[str] = None
    respondent_count: int
    overall_average: Optional[Decimal]
    created_at: datetime
    updated_at: datetime


class EvaluationScoreDetailResponse(BaseModel):
    """Schema for single evaluation score response envelope."""

    status: int
    message: str
    data: Optional[EvaluationScoreOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class EvaluationScoreListResponse(BaseModel):
    """Schema for evaluation scores list response envelope."""

    status: int
    message: str
    data: list[EvaluationScoreOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
