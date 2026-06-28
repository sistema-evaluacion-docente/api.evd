"""
Schemas for the department evaluation summary endpoint.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TeacherRankItem(BaseModel):
    """One teacher entry in the department ranking."""

    rank: int
    teacher_id: int
    institutional_code: str
    name: Optional[str]
    contract_type: Optional[str]
    group_count: int
    overall_average: Optional[float]


class EvaluationSummaryOut(BaseModel):
    """Aggregated statistics for a single evaluation (one department, one period)."""

    evaluation_id: int
    period_code: Optional[str]
    period_name: Optional[str]
    department_average: Optional[float]
    teacher_count: int
    best_teacher: Optional[TeacherRankItem]
    worst_teacher: Optional[TeacherRankItem]
    ranking: list[TeacherRankItem]


class EvaluationSummaryResponse(BaseModel):
    """Response envelope for the summary endpoint."""

    status: int
    message: str
    data: Optional[EvaluationSummaryOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str
