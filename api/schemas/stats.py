"""
Schemas for request and response bodies related to statistics.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel

from api.schemas.academic_group import Modality


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
    data: DepartmentAverageWithPrevious | None = None
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
    data: TeacherAverageWithPrevious | None = None
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
    data: list[TeacherHistoryEntry] | None = None
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
    data: list[TeacherCourseItem] | None = None
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

    academic_period_id: int | None = None
    academic_period_code: str | None = None
    academic_period_name: str | None = None
    department_id: int | None = None
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
    data: TeacherCommentsBySubjectData | None = None
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
    data: TeacherDimensionAveragesData | None = None
    error: str | None = None
    timestamp: datetime
    path: str


class TeacherMatrixCourseItem(BaseModel):
    """Single course row in the teacher evaluation matrix."""

    course_name: str
    question_averages: dict[str, float]
    overall_average: float


class TeacherMatrixData(BaseModel):
    """Full matrix data for a teacher: per-course question averages + column averages."""

    teacher_id: int
    evaluation_id: int
    courses: list[TeacherMatrixCourseItem]
    column_averages: dict[str, float]


class TeacherMatrixResponse(BaseModel):
    """Schema for teacher matrix response envelope."""

    status: int
    message: str
    data: TeacherMatrixData
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


class QuestionComparison(BaseModel):
    """Per-question scores for teacher vs department comparison."""

    code: str
    text: str
    teacher_average: float | None
    department_average: float | None


class DimensionComparison(BaseModel):
    """Per-dimension averages for teacher vs department comparison."""

    dimension: str
    teacher_average: float | None
    department_average: float | None
    questions: list[QuestionComparison]


class TeacherDepartmentComparison(BaseModel):
    """Full teacher vs department comparison for an academic period."""

    teacher_id: int
    academic_period_id: int
    academic_period_code: str | None
    department_id: int | None
    department_name: str | None
    department_overall_average: float | None
    dimensions: list[DimensionComparison]


class TeacherDepartmentComparisonResponse(BaseModel):
    """Response envelope for teacher vs department comparison."""

    status: int
    message: str
    data: TeacherDepartmentComparison | None = None
    error: str | None = None
    timestamp: datetime
    path: str


class SubjectItem(BaseModel):
    """Analytics summary for a single subject (course) in an academic period."""

    course_id: int
    course_code: str
    course_name: str | None
    department_id: int | None
    department_name: str | None
    teacher_count: int
    group_count: int
    overall_average: float | None
    previous_overall_average: float | None
    total_respondents: int
    weakest_dimension: str | None
    strongest_dimension: str | None


class SubjectListResponse(BaseModel):
    """Response envelope for subjects analytics list."""

    status: int
    message: str
    data: list[SubjectItem] | None = None
    error: str | None = None
    timestamp: datetime
    path: str


class SubjectTeacherDimension(BaseModel):
    """Average score for a single dimension for a teacher in a subject."""

    dimension: str
    average: float | None


class SubjectTeacherItem(BaseModel):
    """Teacher entry in a subject's teacher comparison."""

    teacher_id: int
    institutional_code: str
    name: str | None
    avatar_url: str | None
    contract_type: str | None
    group_count: int
    overall_average: float | None
    dimensions: list[SubjectTeacherDimension]


class SubjectTeachersData(BaseModel):
    """All teachers for a subject in an academic period with dimension breakdown."""

    course_id: int
    course_code: str
    course_name: str | None
    academic_period_id: int
    academic_period_code: str
    teachers: list[SubjectTeacherItem]


class SubjectTeachersResponse(BaseModel):
    """Response envelope for subject teachers comparison."""

    status: int
    message: str
    data: SubjectTeachersData | None = None
    error: str | None = None
    timestamp: datetime
    path: str


class DepartmentPeriodRangePeriod(BaseModel):
    """Single academic period included in a period range report."""

    academic_period_id: int
    academic_period_code: str
    academic_period_name: str | None


class DepartmentPeriodRangePeriodAverage(BaseModel):
    """Average scores for a single academic period within a range."""

    academic_period_id: int
    academic_period_code: str
    academic_period_name: str | None
    overall_average: float | None
    total_respondents: int
    evaluation_count: int


class DepartmentPeriodRangeDimension(BaseModel):
    """Average score for a single pedagogical dimension across a period range."""

    dimension: str
    average: float | None
    percentage: float | None


class DepartmentPeriodRangeSubjectGroup(BaseModel):
    """Single academic group (course-teacher-period-group) within a subject."""

    academic_group_id: int
    group_name: str | None
    modality: str | None = None
    course_id: int
    course_code: str
    teacher_id: int | None
    teacher_name: str | None
    teacher_avatar_url: str | None
    academic_period_id: int
    academic_period_code: str
    overall_average: float | None
    respondent_count: int


class DepartmentPeriodRangeSubject(BaseModel):
    """Average scores for a single subject aggregated by subject name across
    a period range, with its academic groups from every period (and every
    underlying course code sharing that name) nested inside."""

    course_name: str | None
    course_codes: list[str]
    teacher_count: int
    group_count: int
    overall_average: float | None
    total_respondents: int
    groups: list[DepartmentPeriodRangeSubjectGroup]


@dataclass
class DepartmentPeriodRangeSubjectFilters:
    """Dataclass to hold filters for the department period-range subjects report."""

    start_period_code: str
    end_period_code: str
    search: str | None = None
    teacher_name: str | None = None
    modality: str | None = None
    sort_by: str | None = None


def department_period_range_subject_filters(
    start_period: str = Query(
        ..., description="Código del periodo inicial (ej. '2020-1')"
    ),
    end_period: str = Query(..., description="Código del periodo final (ej. '2022-1')"),
    search: str | None = Query(
        default=None,
        min_length=1,
        description="Buscar por nombre de la asignatura",
    ),
    teacher_name: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Buscar por nombre del docente. Cuando se envía, los promedios "
            "y conteos de cada asignatura se recalculan solo con los "
            "grupos de ese docente."
        ),
    ),
    modality: Modality | None = Query(
        default=None,
        description=(
            "Filtrar por modalidad del grupo (PRESENCIAL o DISTANCIA). "
            "Cuando se envía, los promedios y conteos de cada asignatura "
            "se recalculan solo con los grupos de esa modalidad. Los grupos "
            "cargados antes de que se registrara la modalidad quedan fuera."
        ),
    ),
    sort_by: str | None = Query(
        default=None,
        description=(
            "Ordenar por: course_name_asc, course_name_desc, "
            "overall_average_asc, overall_average_desc, group_count_asc, "
            "group_count_desc, teacher_count_asc, teacher_count_desc, "
            "total_respondents_asc, total_respondents_desc. "
            "Por defecto: overall_average_desc."
        ),
    ),
) -> DepartmentPeriodRangeSubjectFilters:
    """Dependency function to extract period-range subject filters from query parameters."""

    return DepartmentPeriodRangeSubjectFilters(
        start_period_code=start_period,
        end_period_code=end_period,
        search=search,
        teacher_name=teacher_name,
        modality=modality,
        sort_by=sort_by,
    )


DepartmentPeriodRangeSubjectFiltersDep = Annotated[
    DepartmentPeriodRangeSubjectFilters,
    Depends(department_period_range_subject_filters),
]


class DepartmentPeriodRangeReport(BaseModel):
    """Department overall/per-period averages and pedagogical dimension
    averages aggregated across a range of academic periods."""

    department_id: int
    department_name: str
    department_code: str
    start_period_code: str
    end_period_code: str
    periods: list[DepartmentPeriodRangePeriod]
    overall_average: float | None
    total_respondents: int
    evaluation_count: int
    period_averages: list[DepartmentPeriodRangePeriodAverage]
    dimensions: list[DepartmentPeriodRangeDimension]
    comments_risk_counts: dict[str, int]
    comments_pedagogical_category_counts: dict[str, int]


class DepartmentPeriodRangeReportResponse(BaseModel):
    """Response envelope for the department period range report."""

    status: int
    message: str
    data: DepartmentPeriodRangeReport | None = None
    error: str | None = None
    timestamp: datetime
    path: str


class DepartmentPeriodRangeSubjectsResponse(BaseModel):
    """Response envelope for the department period range subjects list."""

    status: int
    message: str
    data: list[DepartmentPeriodRangeSubject] | None = None
    error: str | None = None
    timestamp: datetime
    path: str
