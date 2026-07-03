"""
Schemas for the department evaluation summary endpoint.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QuestionItem(BaseModel):
    """A single evaluation question with its dimension."""

    code: str
    text: str
    dimension: str


class QuestionCatalogResponse(BaseModel):
    """Response envelope for the questions catalog endpoint."""

    status: int
    message: str
    data: list[QuestionItem]
    timestamp: datetime
    path: str


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


class QuestionScore(BaseModel):
    """Individual question score within a dimension."""

    id: Optional[int] = None
    code: str
    text: str
    score: Optional[float]


class DimensionScore(BaseModel):
    """Average score for one evaluation dimension."""

    dimension: str
    average: Optional[float]
    questions: list[QuestionScore] = []


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


class CourseComments(BaseModel):
    """Comments for a single course group."""

    course_code: str
    course_name: Optional[str]
    group_name: Optional[str]
    comments: list[str]


class TeacherCommentsOut(BaseModel):
    """All comments for a teacher within an evaluation, grouped by course."""

    teacher_id: int
    evaluation_id: int
    courses: list[CourseComments]


class TeacherCommentsResponse(BaseModel):
    """Response envelope for teacher comments endpoint."""

    status: int
    message: str
    data: Optional[TeacherCommentsOut] = None
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


class TeacherPeriodEvaluation(BaseModel):
    """Teacher evaluation summary for a single academic period."""

    teacher_id: int
    avatar_url: Optional[str]
    institutional_code: str
    name: Optional[str]
    contract_type: Optional[str]
    department_name: Optional[str]
    group_count: int
    overall_average: Optional[float]


class TeacherPeriodEvaluationsResponse(BaseModel):
    """Response envelope for the period teacher evaluations endpoint."""

    status: int
    message: str
    data: Optional[list[TeacherPeriodEvaluation]] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class TeacherHistoryResponse(BaseModel):
    """Response envelope for the teacher history endpoint."""

    status: int
    message: str
    data: Optional[TeacherHistoryOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str
