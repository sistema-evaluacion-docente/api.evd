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


class TeacherRankingListResponse(BaseModel):
    """Schema for paginated teacher ranking response envelope."""

    status: int
    message: str
    data: list[TeacherRankItem]
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


class TeacherAverageWithPrevious(BaseModel):
    """Teacher average for a period with comparison to previous period."""

    teacher_id: int
    academic_period_id: int
    academic_period_code: str
    academic_period_name: str | None
    overall_average: float | None
    group_count: int
    previous_academic_period_id: int | None
    previous_academic_period_code: str | None
    previous_academic_period_name: str | None
    previous_overall_average: float | None
    previous_group_count: int | None


class TeacherAverageWithPreviousResponse(BaseModel):
    """Schema for teacher average with previous period response envelope."""

    status: int
    message: str
    data: TeacherAverageWithPrevious
    error: str | None = None
    timestamp: datetime
    path: str


class TeacherHistoryEntry(BaseModel):
    """Teacher average for a single academic period."""

    period_code: str
    period_name: str | None
    overall_average: float | None


class TeacherHistoryResponse(BaseModel):
    """Schema for teacher history response envelope."""

    status: int
    message: str
    data: list[TeacherHistoryEntry]
    error: str | None = None
    timestamp: datetime
    path: str


class TeacherCourseItem(BaseModel):
    """Single course entry with average score for a teacher."""

    course_code: str
    course_name: str | None
    group_name: str | None
    overall_average: float | None


class TeacherCoursesResponse(BaseModel):
    """Schema for teacher courses response envelope."""

    status: int
    message: str
    data: list[TeacherCourseItem]
    error: str | None = None
    timestamp: datetime
    path: str


class GradeDistributionBin(BaseModel):
    """Single bin in the grade distribution histogram."""

    range_label: str
    min_score: float
    max_score: float
    teacher_count: int


class GradeDistribution(BaseModel):
    """Grade distribution histogram data."""

    academic_period_id: int | None
    academic_period_code: str | None
    academic_period_name: str | None
    department_id: int | None
    bins: list[GradeDistributionBin]


class GradeDistributionResponse(BaseModel):
    """Schema for grade distribution response envelope."""

    status: int
    message: str
    data: GradeDistribution
    error: str | None = None
    timestamp: datetime
    path: str


class TeacherCommentSubjectItem(BaseModel):
    """Comment count for a single course/subject."""

    course_code: str
    course_name: str | None
    faculty_name: str | None
    comment_count: int


class TeacherCommentsBySubjectData(BaseModel):
    """Teacher comments grouped by subject for a period."""

    teacher_id: int
    academic_period_id: int
    total_comments: int
    subjects: list[TeacherCommentSubjectItem]


class TeacherCommentsBySubjectResponse(BaseModel):
    """Schema for teacher comments by subject response envelope."""

    status: int
    message: str
    data: TeacherCommentsBySubjectData
    error: str | None = None
    timestamp: datetime
    path: str


class TeacherDimensionAverageItem(BaseModel):
    """Average score for a single evaluation dimension."""

    dimension: str
    average: float | None
    percentage: float | None


class TeacherDimensionAveragesData(BaseModel):
    """Teacher dimension averages for a period."""

    teacher_id: int
    academic_period_id: int
    dimensions: list[TeacherDimensionAverageItem]


class TeacherDimensionAveragesResponse(BaseModel):
    """Schema for teacher dimension averages response envelope."""

    status: int
    message: str
    data: TeacherDimensionAveragesData
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
