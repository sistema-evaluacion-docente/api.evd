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


class DimensionScore(BaseModel):
    """Average score for one evaluation dimension."""

    dimension: str
    average: Optional[float]


class CourseGroupScore(BaseModel):
    """Scores for a single academic group (one course, one group letter)."""

    course_code: str
    course_name: Optional[str]
    group_name: Optional[str]
    respondent_count: int
    overall_average: Optional[float]
    dimensions: list[DimensionScore]


class TeacherEvaluationDetail(BaseModel):
    """Full detail of a teacher within a specific evaluation."""

    teacher_id: int
    institutional_code: str
    name: Optional[str]
    contract_type: Optional[str]
    evaluation_id: int
    period_code: Optional[str]
    period_name: Optional[str]
    overall_average: Optional[float]
    group_count: int
    courses: list[CourseGroupScore]
    dimensions: list[DimensionScore]


class TeacherEvaluationDetailResponse(BaseModel):
    """Response envelope for the teacher detail endpoint."""

    status: int
    message: str
    data: Optional[TeacherEvaluationDetail] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class TeacherPeriodHistory(BaseModel):
    """Teacher average for a single academic period."""

    evaluation_id: int
    period_code: str
    period_name: Optional[str]
    overall_average: Optional[float]
    group_count: int


class TeacherHistoryOut(BaseModel):
    """Full historical record of a teacher across all periods."""

    teacher_id: int
    institutional_code: str
    name: Optional[str]
    history: list[TeacherPeriodHistory]


class TeacherHistoryResponse(BaseModel):
    """Response envelope for the teacher history endpoint."""

    status: int
    message: str
    data: Optional[TeacherHistoryOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str
