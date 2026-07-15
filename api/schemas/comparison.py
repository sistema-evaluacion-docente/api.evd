"""
Schemas for teacher semester comparison responses.
"""

from datetime import datetime

from pydantic import BaseModel


class QuestionComparisonDetail(BaseModel):
    """Per-question score comparison between two semesters."""

    code: str
    text: str
    current_average: float | None
    old_average: float | None
    difference: float | None


class DimensionComparisonDetail(BaseModel):
    """Per-dimension averages comparison between two semesters."""

    dimension: str
    current_average: float | None
    old_average: float | None
    difference: float | None
    questions: list[QuestionComparisonDetail]


class CourseComparisonItem(BaseModel):
    """Course-level comparison between two semesters."""

    course_code: str
    course_name: str | None
    group_name: str | None
    semester: str
    overall_average: float | None
    respondent_count: int | None


class CommentComparisonItem(BaseModel):
    """Comment count comparison for a semester."""

    semester: str
    total_comments: int
    risk_breakdown: dict[str, int]


class TeacherSemesterComparison(BaseModel):
    """Full comparison data between two semesters for a teacher."""

    teacher_id: int
    teacher_name: str | None
    current_semester: str
    old_semester: str
    current_overall_average: float | None
    old_overall_average: float | None
    average_difference: float | None
    current_group_count: int
    old_group_count: int | None
    current_respondent_count: int
    old_respondent_count: int | None
    current_weakest_dimension: str | None
    old_weakest_dimension: str | None
    current_strongest_dimension: str | None
    old_strongest_dimension: str | None
    dimensions: list[DimensionComparisonDetail]
    current_courses: list[CourseComparisonItem]
    old_courses: list[CourseComparisonItem]
    current_comments: CommentComparisonItem | None
    old_comments: CommentComparisonItem | None


class TeacherSemesterComparisonResponse(BaseModel):
    """Response envelope for teacher semester comparison."""

    status: int
    message: str
    data: TeacherSemesterComparison | None = None
    error: str | None = None
    timestamp: datetime
    path: str
