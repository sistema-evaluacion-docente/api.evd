"""
Comparison repository — queries that compare teacher data across two semesters.
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel


class ComparisonRepository:
    """Repository for teacher semester comparison queries."""

    def __init__(self, db: Session):
        self.db = db

    async def get_teacher_info(self, teacher_id: int) -> dict | None:
        """Return basic teacher + user info, or None if not found."""

        row = (
            self.db.query(
                TeacherModel.id.label("teacher_id"),
                UserModel.name.label("teacher_name"),
            )
            .join(UserModel, UserModel.id == TeacherModel.user_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )

        if not row:
            return None

        return {"teacher_id": row.teacher_id, "teacher_name": row.teacher_name}

    async def get_period(self, period_id: int) -> AcademicPeriodModel | None:
        """Return an academic period by ID."""

        return (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

    async def get_overall_stats(
        self, teacher_id: int, period_id: int
    ) -> dict:
        """Return overall average, group count and respondent count for a teacher in a period."""

        row = (
            self.db.query(
                func.avg(EvaluationScoreModel.overall_average).label(
                    "overall_average"),
                func.count(func.distinct(AcademicGroupModel.id)
                           ).label("group_count"),
                func.coalesce(
                    func.sum(EvaluationScoreModel.respondent_count), 0
                ).label("respondent_count"),
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
            .first()
        )

        return {
            "overall_average": (
                round(float(row.overall_average),
                      2) if row.overall_average else None
            ),
            "group_count": row.group_count or 0,
            "respondent_count": row.respondent_count or 0,
        }

    async def get_question_averages(
        self, teacher_id: int, period_id: int
    ) -> dict[str, float]:
        """Return per-question average scores for a teacher in a period."""

        rows = (
            self.db.query(
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label(
                    "avg_score"),
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

        return {
            row.question_code: round(float(row.avg_score), 2) for row in rows
        }

    async def get_courses(
        self, teacher_id: int, period_id: int
    ) -> list[dict]:
        """Return the teacher's courses with averages for a period."""

        rows = (
            self.db.query(
                CourseModel.code.label("course_code"),
                CourseModel.name.label("course_name"),
                AcademicGroupModel.group_name,
                func.avg(EvaluationScoreModel.overall_average).label(
                    "overall_average"),
                func.coalesce(
                    func.sum(EvaluationScoreModel.respondent_count), 0
                ).label("respondent_count"),
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
                EvaluationModel.academic_period_id == period_id,
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
                "overall_average": (
                    round(float(row.overall_average), 2)
                    if row.overall_average
                    else None
                ),
                "respondent_count": row.respondent_count or 0,
            }
            for row in rows
        ]

    async def get_comments_by_risk(
        self, teacher_id: int, period_id: int
    ) -> dict | None:
        """Return comment count and risk-level breakdown for a teacher in a period."""

        rows = (
            self.db.query(
                func.count(CommentModel.id).label("total"),
                RiskLevelModel.name.label("risk_name"),
                func.count(func.distinct(CommentModel.id)).label("risk_count"),
            )
            .join(
                EvaluationModel,
                CommentModel.evaluation_id == EvaluationModel.id,
            )
            .outerjoin(
                RiskLevelModel,
                CommentModel.risk_level == RiskLevelModel.id,
            )
            .filter(
                CommentModel.teacher_id == teacher_id,
                EvaluationModel.academic_period_id == period_id,
            )
            .group_by(RiskLevelModel.name)
            .all()
        )

        if not rows:
            return None

        total = sum(r.total for r in rows)
        risk_breakdown = {
            r.risk_name or "SIN_CLASIFICAR": r.risk_count for r in rows
        }

        return {"total_comments": total, "risk_breakdown": risk_breakdown}


def get_comparison_repository(
    db: Annotated[Session, Depends(get_db)],
):
    """Dependency factory for ComparisonRepository."""

    return ComparisonRepository(db)
