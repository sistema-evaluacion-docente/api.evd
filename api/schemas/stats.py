"""
Schemas for request and response bodies related to statistics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DepartmentPeriodStat(BaseModel):
    """Statistics for a department in a given academic period."""

    department_id: int
    department_name: str
    department_code: str
    academic_period_id: int
    academic_period_code: str
    academic_period_name: Optional[str]
    global_average: Optional[Decimal]
    total_respondents: int
    evaluation_count: int


class TeacherRankItem(BaseModel):
    """Single teacher entry in a performance ranking."""

    teacher_id: int
    institutional_code: str
    name: str
    avatar_url: str | None
    contract_type: str | None
    group_count: int
    overall_average: float | None


class TeacherPerformanceRanking(BaseModel):
    """Top 5 and bottom 5 teachers by average score for a period."""

    academic_period_id: int | None
    academic_period_code: str | None
    academic_period_name: str | None
    top_5: list[TeacherRankItem]
    bottom_5: list[TeacherRankItem]


class TeacherPerformanceResponse(BaseModel):
    """Schema for teacher performance ranking response envelope."""

    status: int
    message: str
    data: TeacherPerformanceRanking
    error: str | None = None
    timestamp: datetime
    path: str


class DepartmentAverageWithPrevious(BaseModel):
    """Department average for a period with comparison to previous period."""

    department_id: int
    department_name: str
    department_code: str
    academic_period_id: int
    academic_period_code: str
    academic_period_name: str | None
    global_average: float | None
    total_respondents: int
    evaluation_count: int
    previous_academic_period_id: int | None
    previous_academic_period_code: str | None
    previous_academic_period_name: str | None
    previous_global_average: float | None
    previous_total_respondents: int | None
    previous_evaluation_count: int | None


class DepartmentAverageWithPreviousResponse(BaseModel):
    """Schema for department average with previous period response envelope."""

    status: int
    message: str
    data: DepartmentAverageWithPrevious
    error: str | None = None
    timestamp: datetime
    path: str


class StatsListResponse(BaseModel):
    """Schema for statistics list response envelope."""

    status: int
    message: str
    data: list[DepartmentPeriodStat]
    error: Optional[str] = None
    timestamp: datetime
    path: str
