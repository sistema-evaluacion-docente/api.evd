"""
Schemas for request and response bodies related to evaluation question scores.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class EvaluationQuestionScoreOut(BaseModel):
    """Schema for outputting an evaluation question score."""

    id: int
    evaluation_score_id: int
    question_code: str
    score: Decimal


class EvaluationQuestionScoreDetailResponse(BaseModel):
    """Schema for single evaluation question score response envelope."""

    status: int
    message: str
    data: Optional[EvaluationQuestionScoreOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class EvaluationQuestionScoreListResponse(BaseModel):
    """Schema for evaluation question scores list response envelope."""

    status: int
    message: str
    data: list[EvaluationQuestionScoreOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
