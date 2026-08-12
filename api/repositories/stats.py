"""
Stats repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.faculty import FacultyModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.schemas.stats import DepartmentPeriodRangeSubjectFilters
from api.utils.dimensions import DIMENSION_MAP, QUESTIONS


class StatsRepository:
    """Stats repository"""

    def __init__(self, db: Session):
        self.db = db

    async def get_department_averages_by_period(
        self, department_id: int | None = None
    ) -> list[dict]:
        """
        Get global average per department per academic period.

        Joins evaluations -> evaluation_scores and groups by
        (department, academic_period).
        """

        query = (
            self.db.query(
                DepartmentModel.id.label("department_id"),
                DepartmentModel.name.label("department_name"),
                DepartmentModel.code.label("department_code"),
                AcademicPeriodModel.id.label("academic_period_id"),
                AcademicPeriodModel.code.label("academic_period_code"),
                AcademicPeriodModel.name.label("academic_period_name"),
                func.avg(EvaluationScoreModel.overall_average).label("global_average"),
                func.sum(EvaluationScoreModel.respondent_count).label(
                    "total_respondents"
                ),
                func.count(EvaluationScoreModel.id).label("evaluation_count"),
            )
            .join(
                EvaluationModel,
                EvaluationModel.department_id == DepartmentModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .join(
                AcademicPeriodModel,
                AcademicPeriodModel.id == EvaluationModel.academic_period_id,
            )
            .group_by(
                DepartmentModel.id,
                DepartmentModel.name,
                DepartmentModel.code,
                AcademicPeriodModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .order_by(
                AcademicPeriodModel.code.desc(),
                DepartmentModel.name,
            )
        )

        if department_id is not None:
            query = query.filter(DepartmentModel.id == department_id)

        results = query.all()

        return [
            {
                "department_id": row.department_id,
                "department_name": row.department_name,
                "department_code": row.department_code,
                "academic_period_id": row.academic_period_id,
                "academic_period_code": row.academic_period_code,
                "academic_period_name": row.academic_period_name,
                "global_average": (
                    float(row.global_average) if row.global_average else None
                ),
                "total_respondents": row.total_respondents,
                "evaluation_count": row.evaluation_count,
            }
            for row in results
        ]

    async def get_department_average_with_previous(
        self, department_id: int, academic_period_id: int
    ) -> dict | None:
        """
        Get department average for a specific academic period and its previous period.
        """

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )

        if not period:
            return None

        def get_stats_for_period(dept_id: int, period_id: int) -> dict | None:
            result = (
                self.db.query(
                    DepartmentModel.id.label("department_id"),
                    DepartmentModel.name.label("department_name"),
                    DepartmentModel.code.label("department_code"),
                    AcademicPeriodModel.id.label("academic_period_id"),
                    AcademicPeriodModel.code.label("academic_period_code"),
                    AcademicPeriodModel.name.label("academic_period_name"),
                    func.avg(EvaluationScoreModel.overall_average).label(
                        "global_average"
                    ),
                    func.sum(EvaluationScoreModel.respondent_count).label(
                        "total_respondents"
                    ),
                    func.count(EvaluationScoreModel.id).label("evaluation_count"),
                )
                .join(
                    EvaluationModel,
                    EvaluationModel.department_id == DepartmentModel.id,
                )
                .join(
                    EvaluationScoreModel,
                    EvaluationScoreModel.evaluation_id == EvaluationModel.id,
                )
                .join(
                    AcademicPeriodModel,
                    AcademicPeriodModel.id == EvaluationModel.academic_period_id,
                )
                .filter(
                    DepartmentModel.id == dept_id,
                    EvaluationModel.academic_period_id == period_id,
                )
                .group_by(
                    DepartmentModel.id,
                    DepartmentModel.name,
                    DepartmentModel.code,
                    AcademicPeriodModel.id,
                    AcademicPeriodModel.code,
                    AcademicPeriodModel.name,
                )
                .first()
            )

            if not result:
                return None

            return {
                "department_id": result.department_id,
                "department_name": result.department_name,
                "department_code": result.department_code,
                "academic_period_id": result.academic_period_id,
                "academic_period_code": result.academic_period_code,
                "academic_period_name": result.academic_period_name,
                "global_average": (
                    float(result.global_average) if result.global_average else None
                ),
                "total_respondents": result.total_respondents,
                "evaluation_count": result.evaluation_count,
            }

        current_stats = get_stats_for_period(department_id, academic_period_id)

        if not current_stats:
            return None

        prev_period_code = await self._get_previous_period_code(period.code)
        previous_stats = None

        if prev_period_code:
            prev_period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.code == prev_period_code)
                .first()
            )

            if prev_period:
                previous_stats = get_stats_for_period(department_id, prev_period.id)

        return {
            **current_stats,
            "previous_academic_period_id": (
                previous_stats["academic_period_id"] if previous_stats else None
            ),
            "previous_academic_period_code": (
                previous_stats["academic_period_code"] if previous_stats else None
            ),
            "previous_academic_period_name": (
                previous_stats["academic_period_name"] if previous_stats else None
            ),
            "previous_global_average": (
                previous_stats["global_average"] if previous_stats else None
            ),
            "previous_total_respondents": (
                previous_stats["total_respondents"] if previous_stats else None
            ),
            "previous_evaluation_count": (
                previous_stats["evaluation_count"] if previous_stats else None
            ),
        }

    async def _get_previous_period_code(self, code: str) -> str | None:
        """Get the previous academic period code from a code like '2025-2'."""

        parts = code.split("-")

        if len(parts) != 2:
            return None

        year = int(parts[0])
        semester = int(parts[1])

        if semester == 1:
            prev_year = year - 1
            prev_semester = 2
        else:
            prev_year = year
            prev_semester = semester - 1

        return f"{prev_year}-{prev_semester}"

    async def get_teacher_performance_ranking(
        self, academic_period_id: int | None = None
    ) -> dict:
        """
        Get top 5 and bottom 5 teachers by overall average score.

        Joins evaluation_scores -> academic_groups -> teachers -> users
        and optionally filters by academic period.
        """

        base_query = (
            self.db.query(
                TeacherModel.id.label("teacher_id"),
                UserModel.institutional_code,
                UserModel.name,
                UserModel.email,
                UserModel.avatar_url,
                TeacherModel.contract_type,
                func.count(EvaluationScoreModel.id).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.teacher_id == TeacherModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(UserModel, UserModel.id == TeacherModel.user_id)
            .group_by(
                TeacherModel.id,
                UserModel.institutional_code,
                UserModel.name,
                UserModel.email,
                UserModel.avatar_url,
                TeacherModel.contract_type,
            )
        )

        if academic_period_id is not None:
            base_query = base_query.filter(
                EvaluationModel.academic_period_id == academic_period_id
            )

        all_teachers = base_query.order_by(
            func.avg(EvaluationScoreModel.overall_average).desc()
        ).all()

        period_info = None
        if academic_period_id is not None:
            period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.id == academic_period_id)
                .first()
            )
            if period:
                period_info = {
                    "academic_period_id": period.id,
                    "academic_period_code": period.code,
                    "academic_period_name": period.name,
                }

        def format_teacher(row) -> dict:
            return {
                "teacher_id": row.teacher_id,
                "institutional_code": row.institutional_code,
                "name": row.name,
                "avatar_url": row.avatar_url,
                "contract_type": row.contract_type,
                "group_count": row.group_count,
                "overall_average": (
                    float(row.overall_average) if row.overall_average else None
                ),
            }

        top_5 = [format_teacher(row) for row in all_teachers[:5]]
        bottom_5 = [format_teacher(row) for row in all_teachers[-5:][::-1]]

        return {
            **(period_info or {}),
            "top_5": top_5,
            "bottom_5": bottom_5,
        }

    async def get_teacher_ranking_paginated(
        self,
        academic_period_id: int | None = None,
        department_id: int | None = None,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
        sort: str = "desc",
    ) -> dict:
        """
        Get paginated teacher ranking by overall average score with search.
        """

        base_query = (
            self.db.query(
                TeacherModel.id.label("teacher_id"),
                UserModel.institutional_code,
                UserModel.name,
                UserModel.email,
                UserModel.avatar_url,
                TeacherModel.contract_type,
                func.count(EvaluationScoreModel.id).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.teacher_id == TeacherModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(UserModel, UserModel.id == TeacherModel.user_id)
        )

        if academic_period_id is not None:
            base_query = base_query.filter(
                EvaluationModel.academic_period_id == academic_period_id
            )

        if department_id is not None:
            base_query = base_query.filter(
                EvaluationModel.department_id == department_id
            )

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
                | (UserModel.institutional_code.ilike(search_pattern))
            )

        count_query = (
            self.db.query(func.count(func.distinct(TeacherModel.id)))
            .join(
                AcademicGroupModel,
                AcademicGroupModel.teacher_id == TeacherModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(UserModel, UserModel.id == TeacherModel.user_id)
        )

        if academic_period_id is not None:
            count_query = count_query.filter(
                EvaluationModel.academic_period_id == academic_period_id
            )

        if department_id is not None:
            count_query = count_query.filter(
                EvaluationModel.department_id == department_id
            )

        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
                | (UserModel.institutional_code.ilike(search_pattern))
            )

        total = count_query.scalar() or 0
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        results = (
            base_query.group_by(
                TeacherModel.id,
                UserModel.institutional_code,
                UserModel.name,
                UserModel.email,
                UserModel.avatar_url,
                TeacherModel.contract_type,
            )
            .order_by(
                func.avg(EvaluationScoreModel.overall_average).desc()
                if sort == "desc"
                else func.avg(EvaluationScoreModel.overall_average).asc()
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "teachers": [
                {
                    "teacher_id": row.teacher_id,
                    "institutional_code": row.institutional_code,
                    "name": row.name,
                    "avatar_url": row.avatar_url,
                    "contract_type": row.contract_type,
                    "group_count": row.group_count,
                    "overall_average": (
                        float(row.overall_average) if row.overall_average else None
                    ),
                }
                for row in results
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_grade_distribution(
        self,
        academic_period_id: int | None = None,
        department_id: int | None = None,
        bin_size: float = 0.5,
    ) -> dict:
        """
        Get grade distribution histogram for teachers.

        Calculates each teacher's overall average and groups them into bins.
        """

        base_query = (
            self.db.query(
                TeacherModel.id.label("teacher_id"),
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.teacher_id == TeacherModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .group_by(TeacherModel.id)
        )

        if academic_period_id is not None:
            base_query = base_query.filter(
                EvaluationModel.academic_period_id == academic_period_id
            )

        if department_id is not None:
            base_query = base_query.filter(
                EvaluationModel.department_id == department_id
            )

        teacher_averages = base_query.all()

        period_info = None

        if academic_period_id is not None:
            period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.id == academic_period_id)
                .first()
            )

            if period:
                period_info = {
                    "academic_period_id": period.id,
                    "academic_period_code": period.code,
                    "academic_period_name": period.name,
                }

        if not teacher_averages:
            return {
                **(period_info or {}),
                "department_id": department_id,
                "bins": [],
            }

        min_possible = 1.0
        max_possible = 5.0

        bins = []
        current = min_possible

        while current < max_possible:
            bin_max = min(current + bin_size, max_possible)

            bins.append(
                {
                    "range_label": f"{current:.1f}-{bin_max:.1f}",
                    "min_score": current,
                    "max_score": bin_max,
                    "teacher_count": 0,
                }
            )

            current = bin_max

        for row in teacher_averages:
            avg = float(row.overall_average) if row.overall_average else None

            if avg is None:
                continue

            for b in bins:
                if b["min_score"] <= avg < b["max_score"]:
                    b["teacher_count"] += 1
                    break

                if avg == max_possible and b["max_score"] == max_possible:
                    b["teacher_count"] += 1
                    break

        return {
            **(period_info or {}),
            "department_id": department_id,
            "bins": bins,
        }

    async def get_teacher_average_with_previous(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """
        Get teacher average for a specific academic period and its previous period.
        """

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )

        if not period:
            return None

        def get_stats_for_period(teacher_id: int, period_id: int) -> dict | None:
            result = (
                self.db.query(
                    TeacherModel.id.label("teacher_id"),
                    AcademicPeriodModel.id.label("academic_period_id"),
                    AcademicPeriodModel.code.label("academic_period_code"),
                    AcademicPeriodModel.name.label("academic_period_name"),
                    func.avg(EvaluationScoreModel.overall_average).label(
                        "overall_average"
                    ),
                    func.count(EvaluationScoreModel.id).label("group_count"),
                )
                .join(
                    AcademicGroupModel,
                    AcademicGroupModel.teacher_id == TeacherModel.id,
                )
                .join(
                    EvaluationScoreModel,
                    EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
                )
                .join(
                    EvaluationModel,
                    EvaluationModel.id == EvaluationScoreModel.evaluation_id,
                )
                .join(
                    AcademicPeriodModel,
                    AcademicPeriodModel.id == EvaluationModel.academic_period_id,
                )
                .filter(
                    TeacherModel.id == teacher_id,
                    EvaluationModel.academic_period_id == period_id,
                )
                .group_by(
                    TeacherModel.id,
                    AcademicPeriodModel.id,
                    AcademicPeriodModel.code,
                    AcademicPeriodModel.name,
                )
                .first()
            )

            if not result:
                return None

            return {
                "teacher_id": result.teacher_id,
                "academic_period_id": result.academic_period_id,
                "academic_period_code": result.academic_period_code,
                "academic_period_name": result.academic_period_name,
                "overall_average": (
                    float(result.overall_average) if result.overall_average else None
                ),
                "group_count": result.group_count,
            }

        current_stats = get_stats_for_period(teacher_id, academic_period_id)

        if not current_stats:
            return None

        prev_period_code = await self._get_previous_period_code(period.code)
        previous_stats = None

        if prev_period_code:
            prev_period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.code == prev_period_code)
                .first()
            )

            if prev_period:
                previous_stats = get_stats_for_period(teacher_id, prev_period.id)

        return {
            **current_stats,
            "previous_academic_period_id": (
                previous_stats["academic_period_id"] if previous_stats else None
            ),
            "previous_academic_period_code": (
                previous_stats["academic_period_code"] if previous_stats else None
            ),
            "previous_academic_period_name": (
                previous_stats["academic_period_name"] if previous_stats else None
            ),
            "previous_overall_average": (
                previous_stats["overall_average"] if previous_stats else None
            ),
            "previous_group_count": (
                previous_stats["group_count"] if previous_stats else None
            ),
        }

    async def get_teacher_history(self, teacher_id: int) -> list[dict] | None:
        """Return the teacher's average score for each academic period."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        rows = (
            self.db.query(
                AcademicPeriodModel.code.label("period_code"),
                AcademicPeriodModel.name.label("period_name"),
                func.avg(EvaluationScoreModel.overall_average).label("avg_score"),
            )
            .join(
                EvaluationModel,
                EvaluationModel.academic_period_id == AcademicPeriodModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .filter(AcademicGroupModel.teacher_id == teacher_id)
            .group_by(
                AcademicPeriodModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .order_by(AcademicPeriodModel.code.asc())
            .all()
        )

        return [
            {
                "period_code": row.period_code,
                "period_name": row.period_name,
                "overall_average": float(row.avg_score) if row.avg_score else None,
            }
            for row in rows
        ]

    async def get_teacher_courses_by_period(
        self, teacher_id: int, academic_period_id: int
    ) -> list[dict] | None:
        """Return the teacher's courses with their averages for a given academic period."""

        from api.models.course import CourseModel

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        rows = (
            self.db.query(
                CourseModel.code.label("course_code"),
                CourseModel.name.label("course_name"),
                AcademicGroupModel.group_name,
                func.avg(EvaluationScoreModel.overall_average).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(
                CourseModel.id,
                CourseModel.code,
                CourseModel.name,
                AcademicGroupModel.group_name,
            )
            .order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .all()
        )

        return [
            {
                "course_code": row.course_code,
                "course_name": row.course_name,
                "group_name": row.group_name,
                "overall_average": float(row.avg_score) if row.avg_score else None,
            }
            for row in rows
        ]

    async def get_teacher_comments_by_subject(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Return comments grouped by course/subject for a teacher in a period."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        rows = (
            self.db.query(
                CourseModel.code.label("course_code"),
                CourseModel.name.label("course_name"),
                FacultyModel.name.label("faculty_name"),
                func.count(CommentModel.id).label("comment_count"),
            )
            .join(
                EvaluationModel,
                CommentModel.evaluation_id == EvaluationModel.id,
            )
            .join(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .join(
                DepartmentModel,
                CourseModel.department_id == DepartmentModel.id,
            )
            .outerjoin(
                FacultyModel,
                DepartmentModel.faculty_id == FacultyModel.id,
            )
            .filter(
                CommentModel.teacher_id == teacher_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(
                CourseModel.id,
                CourseModel.code,
                CourseModel.name,
                FacultyModel.name,
            )
            .order_by(func.count(CommentModel.id).desc())
            .all()
        )

        subjects = [
            {
                "course_code": row.course_code,
                "course_name": row.course_name,
                "faculty_name": row.faculty_name,
                "comment_count": row.comment_count,
            }
            for row in rows
        ]

        total_comments = sum(s["comment_count"] for s in subjects)

        return {
            "teacher_id": teacher_id,
            "academic_period_id": academic_period_id,
            "total_comments": total_comments,
            "subjects": subjects,
        }

    async def get_teacher_dimension_averages(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Return dimension-level averages for a teacher in a period."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        eval_scores = (
            self.db.query(EvaluationScoreModel)
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .all()
        )

        accumulated: dict[str, list[float]] = {}

        for eval_score in eval_scores:
            q_scores = (
                self.db.query(EvaluationQuestionScoreModel)
                .filter(
                    EvaluationQuestionScoreModel.evaluation_score_id == eval_score.id
                )
                .all()
            )

            for qs in q_scores:
                accumulated.setdefault(qs.question_code, []).append(float(qs.score))

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            dim_scores = [s for c in codes for s in accumulated.get(c, [])]
            avg = round(sum(dim_scores) / len(dim_scores), 2) if dim_scores else None
            percentage = round(avg * 20, 2) if avg is not None else None
            dimensions.append(
                {
                    "dimension": dim_name,
                    "average": avg,
                    "percentage": percentage,
                }
            )

        return {
            "teacher_id": teacher_id,
            "academic_period_id": academic_period_id,
            "dimensions": dimensions,
        }

    async def get_teacher_matrix(
        self, teacher_id: int, evaluation_id: int
    ) -> dict | None:
        """Return per-course per-question averages matrix for a teacher in an evaluation."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        rows = (
            self.db.query(
                CourseModel.name.label("course_name"),
                AcademicGroupModel.group_name,
                EvaluationQuestionScoreModel.question_code,
                EvaluationQuestionScoreModel.score,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .join(
                EvaluationQuestionScoreModel,
                EvaluationQuestionScoreModel.evaluation_score_id
                == EvaluationScoreModel.id,
            )
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                EvaluationScoreModel.evaluation_id == evaluation_id,
            )
            .all()
        )

        course_data: dict[str, dict[str, list[float]]] = {}

        for row in rows:
            key = f"{row.course_name} ({row.group_name})"
            if key not in course_data:
                course_data[key] = {}
            if row.question_code not in course_data[key]:
                course_data[key][row.question_code] = []
            course_data[key][row.question_code].append(float(row.score))

        courses = []
        all_question_avgs: dict[str, list[float]] = {}

        for course_name, questions in course_data.items():
            question_averages = {}
            total = 0.0
            count = 0

            for q_code in sorted(questions.keys()):
                scores = questions[q_code]
                avg = round(sum(scores) / len(scores), 2)
                question_averages[q_code] = avg
                all_question_avgs.setdefault(q_code, []).append(avg)
                total += avg
                count += 1

            overall = round(total / count, 2) if count > 0 else 0.0

            courses.append(
                {
                    "course_name": course_name,
                    "question_averages": question_averages,
                    "overall_average": overall,
                }
            )

        column_averages = {}
        for q_code, avgs in sorted(all_question_avgs.items()):
            column_averages[q_code] = round(sum(avgs) / len(avgs), 2)

        return {
            "teacher_id": teacher_id,
            "evaluation_id": evaluation_id,
            "courses": courses,
            "column_averages": column_averages,
        }

    async def get_teacher_vs_department(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """
        Compare a teacher's per-question and per-dimension averages against
        the department averages for a given academic period.
        """

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )
        if not teacher:
            return None

        department_id = teacher.department_id

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        period_code = period.code if period else None

        department = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )
        department_name = department.name if department else None

        # Teacher per-question averages
        teacher_rows = (
            self.db.query(
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(EvaluationQuestionScoreModel.question_code)
            .all()
        )
        teacher_by_code: dict[str, float] = {
            row.question_code: round(float(row.avg_score), 2) for row in teacher_rows
        }

        # Department per-question averages
        dept_rows = (
            self.db.query(
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(EvaluationQuestionScoreModel.question_code)
            .all()
        )
        dept_by_code: dict[str, float] = {
            row.question_code: round(float(row.avg_score), 2) for row in dept_rows
        }

        question_text = {q["code"]: q["text"] for q in QUESTIONS}

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            questions = []
            for code in codes:
                questions.append(
                    {
                        "code": code,
                        "text": question_text.get(code, code),
                        "teacher_average": teacher_by_code.get(code),
                        "department_average": dept_by_code.get(code),
                    }
                )

            teacher_dim = [teacher_by_code[c] for c in codes if c in teacher_by_code]
            dept_dim = [dept_by_code[c] for c in codes if c in dept_by_code]

            dimensions.append(
                {
                    "dimension": dim_name,
                    "teacher_average": (
                        round(sum(teacher_dim) / len(teacher_dim), 2)
                        if teacher_dim
                        else None
                    ),
                    "department_average": (
                        round(sum(dept_dim) / len(dept_dim), 2) if dept_dim else None
                    ),
                    "questions": questions,
                }
            )

        all_dept_scores = list(dept_by_code.values())
        dept_overall = (
            round(sum(all_dept_scores) / len(all_dept_scores), 2)
            if all_dept_scores
            else None
        )

        return {
            "teacher_id": teacher_id,
            "academic_period_id": academic_period_id,
            "academic_period_code": period_code,
            "department_id": department_id,
            "department_name": department_name,
            "department_overall_average": dept_overall,
            "dimensions": dimensions,
        }

    async def get_teacher_vs_previous_period(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """
        Compare a teacher's per-question and per-dimension averages between
        the current academic period and the previous one.
        """

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )
        if not teacher:
            return None

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        if not period:
            return None

        def get_question_averages(period_id: int) -> dict[str, float]:
            rows = (
                self.db.query(
                    EvaluationQuestionScoreModel.question_code,
                    func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
                )
                .join(
                    EvaluationScoreModel,
                    EvaluationScoreModel.id
                    == EvaluationQuestionScoreModel.evaluation_score_id,
                )
                .join(
                    AcademicGroupModel,
                    AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
                )
                .join(
                    EvaluationModel,
                    EvaluationModel.id == EvaluationScoreModel.evaluation_id,
                )
                .filter(
                    AcademicGroupModel.teacher_id == teacher_id,
                    EvaluationModel.academic_period_id == period_id,
                )
                .group_by(EvaluationQuestionScoreModel.question_code)
                .all()
            )
            return {row.question_code: round(float(row.avg_score), 2) for row in rows}

        current_by_code = get_question_averages(academic_period_id)

        prev_period_code = await self._get_previous_period_code(period.code)
        prev_period = None
        previous_by_code: dict[str, float] = {}

        if prev_period_code:
            prev_period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.code == prev_period_code)
                .first()
            )
            if prev_period:
                previous_by_code = get_question_averages(prev_period.id)

        question_text = {q["code"]: q["text"] for q in QUESTIONS}

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            questions = []
            for code in codes:
                questions.append(
                    {
                        "code": code,
                        "text": question_text.get(code, code),
                        "current_average": current_by_code.get(code),
                        "previous_average": previous_by_code.get(code),
                    }
                )

            current_dim = [current_by_code[c] for c in codes if c in current_by_code]
            prev_dim = [previous_by_code[c] for c in codes if c in previous_by_code]

            dimensions.append(
                {
                    "dimension": dim_name,
                    "current_average": (
                        round(sum(current_dim) / len(current_dim), 2)
                        if current_dim
                        else None
                    ),
                    "previous_average": (
                        round(sum(prev_dim) / len(prev_dim), 2) if prev_dim else None
                    ),
                    "questions": questions,
                }
            )

        all_current_scores = list(current_by_code.values())
        current_overall = (
            round(sum(all_current_scores) / len(all_current_scores), 2)
            if all_current_scores
            else None
        )

        all_prev_scores = list(previous_by_code.values())
        previous_overall = (
            round(sum(all_prev_scores) / len(all_prev_scores), 2)
            if all_prev_scores
            else None
        )

        return {
            "teacher_id": teacher_id,
            "academic_period_id": academic_period_id,
            "academic_period_code": period.code,
            "previous_academic_period_id": prev_period.id if prev_period else None,
            "previous_academic_period_code": prev_period_code,
            "current_overall_average": current_overall,
            "previous_overall_average": previous_overall,
            "dimensions": dimensions,
        }

    async def get_subjects(
        self, academic_period_id: int, department_id: int | None = None
    ) -> list[dict]:
        """Return subjects (courses) with analytics for a given academic period."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        if not period:
            return []

        base_q = (
            self.db.query(
                CourseModel.id.label("course_id"),
                CourseModel.code.label("course_code"),
                CourseModel.name.label("course_name"),
                DepartmentModel.id.label("department_id"),
                DepartmentModel.name.label("department_name"),
                func.count(func.distinct(AcademicGroupModel.teacher_id)).label(
                    "teacher_count"
                ),
                func.count(func.distinct(AcademicGroupModel.id)).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
                func.sum(EvaluationScoreModel.respondent_count).label(
                    "total_respondents"
                ),
            )
            .join(AcademicGroupModel, AcademicGroupModel.course_id == CourseModel.id)
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .outerjoin(DepartmentModel, DepartmentModel.id == CourseModel.department_id)
            .filter(EvaluationModel.academic_period_id == academic_period_id)
        )

        if department_id is not None:
            base_q = base_q.filter(EvaluationModel.department_id == department_id)

        rows = (
            base_q.group_by(
                CourseModel.id,
                CourseModel.code,
                CourseModel.name,
                DepartmentModel.id,
                DepartmentModel.name,
            )
            .order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .all()
        )

        if not rows:
            return []

        course_ids = [row.course_id for row in rows]

        prev_period_code = await self._get_previous_period_code(period.code)
        prev_avg_by_course: dict[int, float | None] = {}

        if prev_period_code:
            prev_period = (
                self.db.query(AcademicPeriodModel)
                .filter(AcademicPeriodModel.code == prev_period_code)
                .first()
            )
            if prev_period:
                prev_q = (
                    self.db.query(
                        CourseModel.id.label("course_id"),
                        func.avg(EvaluationScoreModel.overall_average).label("avg"),
                    )
                    .join(
                        AcademicGroupModel,
                        AcademicGroupModel.course_id == CourseModel.id,
                    )
                    .join(
                        EvaluationScoreModel,
                        EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
                    )
                    .join(
                        EvaluationModel,
                        EvaluationModel.id == EvaluationScoreModel.evaluation_id,
                    )
                    .filter(
                        EvaluationModel.academic_period_id == prev_period.id,
                        CourseModel.id.in_(course_ids),
                    )
                )
                if department_id is not None:
                    prev_q = prev_q.filter(
                        EvaluationModel.department_id == department_id
                    )
                prev_rows = prev_q.group_by(CourseModel.id).all()
                prev_avg_by_course = {
                    r.course_id: float(r.avg) if r.avg else None for r in prev_rows
                }

        qs_q = (
            self.db.query(
                CourseModel.id.label("course_id"),
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(CourseModel, CourseModel.id == AcademicGroupModel.course_id)
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                EvaluationModel.academic_period_id == academic_period_id,
                CourseModel.id.in_(course_ids),
            )
        )
        if department_id is not None:
            qs_q = qs_q.filter(EvaluationModel.department_id == department_id)

        qs_rows = qs_q.group_by(
            CourseModel.id, EvaluationQuestionScoreModel.question_code
        ).all()

        course_q_scores: dict[int, dict[str, float]] = {}
        for qs in qs_rows:
            course_q_scores.setdefault(qs.course_id, {})[qs.question_code] = float(
                qs.avg_score
            )

        weakest_dim_by_course: dict[int, str | None] = {}
        strongest_dim_by_course: dict[int, str | None] = {}
        for cid, q_scores in course_q_scores.items():
            worst_dim = None
            worst_avg = float("inf")
            best_dim = None
            best_avg = float("-inf")
            for dim_name, codes in DIMENSION_MAP.items():
                dim_scores = [q_scores[c] for c in codes if c in q_scores]
                if dim_scores:
                    avg = sum(dim_scores) / len(dim_scores)
                    if avg < worst_avg:
                        worst_avg = avg
                        worst_dim = dim_name
                    if avg > best_avg:
                        best_avg = avg
                        best_dim = dim_name
            weakest_dim_by_course[cid] = worst_dim
            strongest_dim_by_course[cid] = best_dim

        return [
            {
                "course_id": row.course_id,
                "course_code": row.course_code,
                "course_name": row.course_name,
                "department_id": row.department_id,
                "department_name": row.department_name,
                "teacher_count": row.teacher_count,
                "group_count": row.group_count,
                "overall_average": (
                    float(row.overall_average) if row.overall_average else None
                ),
                "previous_overall_average": prev_avg_by_course.get(row.course_id),
                "total_respondents": row.total_respondents or 0,
                "weakest_dimension": weakest_dim_by_course.get(row.course_id),
                "strongest_dimension": strongest_dim_by_course.get(row.course_id),
            }
            for row in rows
        ]

    def _get_periods_in_range(
        self, start_period_code: str, end_period_code: str
    ) -> list[AcademicPeriodModel]:
        """Return academic periods whose code falls within [start, end]."""

        return (
            self.db.query(AcademicPeriodModel)
            .filter(
                AcademicPeriodModel.code >= start_period_code,
                AcademicPeriodModel.code <= end_period_code,
            )
            .order_by(AcademicPeriodModel.code.asc())
            .all()
        )

    def _get_department_comment_risk_counts(
        self, department_id: int, period_ids: list[int]
    ) -> dict[str, int]:
        """Count comments by risk level (BAJO/MEDIO/ALTO) for a department
        across a set of academic periods."""

        rows = (
            self.db.query(RiskLevelModel.name, func.count(CommentModel.id))
            .join(CommentModel, CommentModel.risk_level == RiskLevelModel.id)
            .join(
                EvaluationModel,
                EvaluationModel.id == CommentModel.evaluation_id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id.in_(period_ids),
            )
            .group_by(RiskLevelModel.name)
            .all()
        )

        counts = {"BAJO": 0, "MEDIO": 0, "ALTO": 0}
        counts.update(dict(rows))

        return counts

    async def get_department_period_range_report(
        self,
        department_id: int,
        start_period_code: str,
        end_period_code: str,
    ) -> dict | None:
        """
        Get a department's overall/per-period averages and pedagogical
        dimension averages aggregated across a range of academic periods
        (e.g. from "2020-1" to "2022-1").
        """

        department = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        if not department:
            return None

        periods = self._get_periods_in_range(start_period_code, end_period_code)

        base_result = {
            "department_id": department.id,
            "department_name": department.name,
            "department_code": department.code,
            "start_period_code": start_period_code,
            "end_period_code": end_period_code,
            "periods": [
                {
                    "academic_period_id": period.id,
                    "academic_period_code": period.code,
                    "academic_period_name": period.name,
                }
                for period in periods
            ],
        }

        period_ids = [period.id for period in periods]

        if not period_ids:
            return {
                **base_result,
                "overall_average": None,
                "total_respondents": 0,
                "evaluation_count": 0,
                "period_averages": [],
                "dimensions": [],
                "comments_risk_counts": {"BAJO": 0, "MEDIO": 0, "ALTO": 0},
            }

        overall_row = (
            self.db.query(
                func.avg(EvaluationScoreModel.overall_average).label("global_average"),
                func.sum(EvaluationScoreModel.respondent_count).label(
                    "total_respondents"
                ),
                func.count(EvaluationScoreModel.id).label("evaluation_count"),
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id.in_(period_ids),
            )
            .first()
        )

        period_rows = (
            self.db.query(
                AcademicPeriodModel.id.label("academic_period_id"),
                AcademicPeriodModel.code.label("academic_period_code"),
                AcademicPeriodModel.name.label("academic_period_name"),
                func.avg(EvaluationScoreModel.overall_average).label("global_average"),
                func.sum(EvaluationScoreModel.respondent_count).label(
                    "total_respondents"
                ),
                func.count(EvaluationScoreModel.id).label("evaluation_count"),
            )
            .join(
                EvaluationModel,
                EvaluationModel.academic_period_id == AcademicPeriodModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                AcademicPeriodModel.id.in_(period_ids),
            )
            .group_by(
                AcademicPeriodModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .order_by(AcademicPeriodModel.code.asc())
            .all()
        )

        question_rows = (
            self.db.query(
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id.in_(period_ids),
            )
            .group_by(EvaluationQuestionScoreModel.question_code)
            .all()
        )
        question_avg_by_code = {
            row.question_code: float(row.avg_score) for row in question_rows
        }

        comments_risk_counts = self._get_department_comment_risk_counts(
            department_id, period_ids
        )

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            dim_scores = [
                question_avg_by_code[code]
                for code in codes
                if code in question_avg_by_code
            ]
            avg = round(sum(dim_scores) / len(dim_scores), 2) if dim_scores else None
            dimensions.append(
                {
                    "dimension": dim_name,
                    "average": avg,
                    "percentage": round(avg * 20, 2) if avg is not None else None,
                }
            )

        return {
            **base_result,
            "overall_average": (
                float(overall_row.global_average)
                if overall_row.global_average
                else None
            ),
            "total_respondents": overall_row.total_respondents or 0,
            "evaluation_count": overall_row.evaluation_count or 0,
            "period_averages": [
                {
                    "academic_period_id": row.academic_period_id,
                    "academic_period_code": row.academic_period_code,
                    "academic_period_name": row.academic_period_name,
                    "overall_average": (
                        float(row.global_average) if row.global_average else None
                    ),
                    "total_respondents": row.total_respondents or 0,
                    "evaluation_count": row.evaluation_count,
                }
                for row in period_rows
            ],
            "dimensions": dimensions,
            "comments_risk_counts": comments_risk_counts,
        }

    async def get_department_period_range_subjects(
        self,
        department_id: int,
        filters: DepartmentPeriodRangeSubjectFilters,
        pagination: PaginationParams,
    ) -> tuple[list[dict], int] | None:
        """
        Get a department's subject (course) averages aggregated across a
        range of academic periods (e.g. from "2020-1" to "2022-1"), one
        entry per subject with its academic groups from every period
        nested inside. Subjects can be filtered by subject name and/or
        teacher name, sorted, and are paginated. When filtered by teacher
        name, averages/counts are recomputed over that teacher's groups
        only (not the whole subject).

        Returns None when the department doesn't exist.
        """

        department = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        if not department:
            return None

        periods = self._get_periods_in_range(
            filters.start_period_code, filters.end_period_code
        )
        period_ids = [period.id for period in periods]

        if not period_ids:
            return [], 0

        search_term = filters.search.strip() if filters.search else None
        teacher_name_term = (
            filters.teacher_name.strip() if filters.teacher_name else None
        )

        def _base_query(*columns):
            """Build the common department/period/subject/teacher-name query."""

            query = (
                self.db.query(*columns)
                .join(
                    AcademicGroupModel, AcademicGroupModel.course_id == CourseModel.id
                )
                .join(
                    EvaluationScoreModel,
                    EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
                )
                .join(
                    EvaluationModel,
                    EvaluationModel.id == EvaluationScoreModel.evaluation_id,
                )
                .join(
                    AcademicPeriodModel,
                    AcademicPeriodModel.id == AcademicGroupModel.academic_period_id,
                )
                .outerjoin(
                    TeacherModel, TeacherModel.id == AcademicGroupModel.teacher_id
                )
                .outerjoin(UserModel, UserModel.id == TeacherModel.user_id)
                .filter(
                    EvaluationModel.department_id == department_id,
                    EvaluationModel.academic_period_id.in_(period_ids),
                )
            )

            if search_term:
                query = query.filter(CourseModel.name.ilike(f"%{search_term}%"))

            if teacher_name_term:
                query = query.filter(UserModel.name.ilike(f"%{teacher_name_term}%"))

            return query

        sort_by = filters.sort_by

        def _apply_sort(query):
            if sort_by == "course_name_asc":
                return query.order_by(CourseModel.name.asc())
            if sort_by == "course_name_desc":
                return query.order_by(CourseModel.name.desc())
            if sort_by == "overall_average_asc":
                return query.order_by(
                    func.avg(EvaluationScoreModel.overall_average).asc()
                )
            if sort_by == "overall_average_desc":
                return query.order_by(
                    func.avg(EvaluationScoreModel.overall_average).desc()
                )
            if sort_by == "group_count_asc":
                return query.order_by(
                    func.count(func.distinct(AcademicGroupModel.id)).asc()
                )
            if sort_by == "group_count_desc":
                return query.order_by(
                    func.count(func.distinct(AcademicGroupModel.id)).desc()
                )
            if sort_by == "teacher_count_asc":
                return query.order_by(
                    func.count(func.distinct(AcademicGroupModel.teacher_id)).asc()
                )
            if sort_by == "teacher_count_desc":
                return query.order_by(
                    func.count(func.distinct(AcademicGroupModel.teacher_id)).desc()
                )
            if sort_by == "total_respondents_asc":
                return query.order_by(
                    func.sum(EvaluationScoreModel.respondent_count).asc()
                )
            if sort_by == "total_respondents_desc":
                return query.order_by(
                    func.sum(EvaluationScoreModel.respondent_count).desc()
                )
            # Default (also covers "overall_average_desc")
            return query.order_by(func.avg(EvaluationScoreModel.overall_average).desc())

        # Different course rows (course_id/code) can carry the same subject
        # name across periods (e.g. re-parsed with a different code), so
        # subjects are merged by name rather than by course_id/code.
        count_query = _base_query(func.count(func.distinct(CourseModel.name)))
        total = count_query.scalar() or 0

        subject_query = _base_query(
            CourseModel.name.label("course_name"),
            func.count(func.distinct(AcademicGroupModel.teacher_id)).label(
                "teacher_count"
            ),
            func.count(func.distinct(AcademicGroupModel.id)).label("group_count"),
            func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
            func.sum(EvaluationScoreModel.respondent_count).label("total_respondents"),
        )

        subject_rows = (
            _apply_sort(subject_query.group_by(CourseModel.name))
            .offset(pagination.offset)
            .limit(pagination.limit)
            .all()
        )

        if not subject_rows:
            return [], total

        subject_names = [row.course_name for row in subject_rows]

        group_rows = (
            _base_query(
                CourseModel.name.label("course_name"),
                CourseModel.id.label("course_id"),
                CourseModel.code.label("course_code"),
                AcademicGroupModel.id.label("academic_group_id"),
                AcademicGroupModel.group_name,
                TeacherModel.id.label("teacher_id"),
                UserModel.name.label("teacher_name"),
                UserModel.avatar_url.label("teacher_avatar_url"),
                AcademicPeriodModel.id.label("academic_period_id"),
                AcademicPeriodModel.code.label("academic_period_code"),
                EvaluationScoreModel.overall_average,
                EvaluationScoreModel.respondent_count,
            )
            .filter(CourseModel.name.in_(subject_names))
            .order_by(
                AcademicPeriodModel.code.asc(),
                AcademicGroupModel.group_name.asc(),
            )
            .all()
        )

        groups_by_name: dict[str | None, list[dict]] = {}
        course_codes_by_name: dict[str | None, list[str]] = {}
        for row in group_rows:
            groups_by_name.setdefault(row.course_name, []).append(
                {
                    "academic_group_id": row.academic_group_id,
                    "group_name": row.group_name,
                    "course_id": row.course_id,
                    "course_code": row.course_code,
                    "teacher_id": row.teacher_id,
                    "teacher_name": row.teacher_name,
                    "teacher_avatar_url": row.teacher_avatar_url,
                    "academic_period_id": row.academic_period_id,
                    "academic_period_code": row.academic_period_code,
                    "overall_average": (
                        float(row.overall_average) if row.overall_average else None
                    ),
                    "respondent_count": row.respondent_count,
                }
            )
            codes = course_codes_by_name.setdefault(row.course_name, [])
            if row.course_code not in codes:
                codes.append(row.course_code)

        items = [
            {
                "course_name": row.course_name,
                "course_codes": course_codes_by_name.get(row.course_name, []),
                "teacher_count": row.teacher_count,
                "group_count": row.group_count,
                "overall_average": (
                    float(row.overall_average) if row.overall_average else None
                ),
                "total_respondents": row.total_respondents or 0,
                "groups": groups_by_name.get(row.course_name, []),
            }
            for row in subject_rows
        ]

        return items, total

    async def get_subject_teachers(
        self, course_id: int, academic_period_id: int
    ) -> dict | None:
        """Return teachers for a subject with per-dimension averages."""

        from api.models.user import UserModel as UserModelLocal

        course = self.db.query(CourseModel).filter(CourseModel.id == course_id).first()
        if not course:
            return None

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        if not period:
            return None

        teacher_rows = (
            self.db.query(
                TeacherModel.id.label("teacher_id"),
                UserModel.institutional_code,
                TeacherModel.contract_type,
                UserModelLocal.name,
                UserModelLocal.avatar_url,
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
                func.count(func.distinct(AcademicGroupModel.id)).label("group_count"),
            )
            .join(AcademicGroupModel, AcademicGroupModel.teacher_id == TeacherModel.id)
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(UserModelLocal, UserModelLocal.id == TeacherModel.user_id)
            .filter(
                AcademicGroupModel.course_id == course_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(
                TeacherModel.id,
                UserModel.institutional_code,
                TeacherModel.contract_type,
                UserModelLocal.name,
                UserModelLocal.avatar_url,
            )
            .order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .all()
        )

        if not teacher_rows:
            return {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "academic_period_id": academic_period_id,
                "academic_period_code": period.code,
                "teachers": [],
            }

        teacher_ids = [row.teacher_id for row in teacher_rows]

        qs_rows = (
            self.db.query(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.course_id == course_id,
                EvaluationModel.academic_period_id == academic_period_id,
                AcademicGroupModel.teacher_id.in_(teacher_ids),
            )
            .group_by(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
            )
            .all()
        )

        teacher_q_scores: dict[int, dict[str, float]] = {}
        for qs in qs_rows:
            teacher_q_scores.setdefault(qs.teacher_id, {})[qs.question_code] = float(
                qs.avg_score
            )

        teachers = []
        for row in teacher_rows:
            q_scores = teacher_q_scores.get(row.teacher_id, {})
            dimensions = []
            for dim_name, codes in DIMENSION_MAP.items():
                dim_scores = [q_scores[c] for c in codes if c in q_scores]
                avg = (
                    round(sum(dim_scores) / len(dim_scores), 2) if dim_scores else None
                )
                dimensions.append({"dimension": dim_name, "average": avg})

            teachers.append(
                {
                    "teacher_id": row.teacher_id,
                    "institutional_code": row.institutional_code,
                    "name": row.name,
                    "avatar_url": row.avatar_url,
                    "contract_type": row.contract_type,
                    "group_count": row.group_count,
                    "overall_average": (
                        float(row.overall_average) if row.overall_average else None
                    ),
                    "dimensions": dimensions,
                }
            )

        return {
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "academic_period_id": academic_period_id,
            "academic_period_code": period.code,
            "teachers": teachers,
        }


def get_stats_repository(db: Annotated[Session, Depends(get_db)]):
    """Get stats repository"""

    return StatsRepository(db)
