"""
Evaluations repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.course import CourseModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.serializers.evaluations import evaluation_to_dict

DIMENSION_MAP = {
    "Desarrollo del Conocimiento": ["001", "002", "003", "004", "005", "006"],
    "Desempeño Docente": ["007", "008", "009", "010", "011", "012", "013", "014"],
    "Procesos de Evaluación": ["015", "016", "017", "018"],
    "Integración Interpersonal": ["019", "020", "021", "022"],
}


class EvaluationsRepository:
    """Evaluations repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        user_id: str,
        academic_period_id: int,
        department_id: int,
        pdf_url: str,
        status: str = "PENDING",
    ) -> dict:
        """Create a new evaluation record."""

        evaluation = EvaluationModel(
            user_id=user_id,
            academic_period_id=academic_period_id,
            department_id=department_id,
            pdf_url=pdf_url,
            status=status,
            count=None,
        )

        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation_to_dict(evaluation)

    async def get_all(
        self,
        period_id: int | None = None,
        department_id: int | None = None,
    ) -> list[dict]:
        """Get all evaluations with optional filters."""

        query = self.db.query(EvaluationModel)

        if period_id is not None:
            query = query.filter(EvaluationModel.academic_period_id == period_id)
        if department_id is not None:
            query = query.filter(EvaluationModel.department_id == department_id)

        evaluations = query.order_by(EvaluationModel.created_at.desc()).all()

        return [evaluation_to_dict(e) for e in evaluations]

    async def get_by_id(self, evaluation_id: int) -> dict | None:
        """Get an evaluation by ID."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if not evaluation:
            return None

        return evaluation_to_dict(evaluation)

    async def get_by_period_and_department(
        self, academic_period_id: int, department_id: int
    ) -> dict | None:
        """Get an evaluation by period and department combination."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(
                EvaluationModel.academic_period_id == academic_period_id,
                EvaluationModel.department_id == department_id,
            )
            .first()
        )

        if not evaluation:
            return None

        return evaluation_to_dict(evaluation)

    async def update_active_status(
        self, evaluation_id: int, active: bool
    ) -> dict | None:
        """Activate or deactivate an evaluation."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if not evaluation:
            return None

        setattr(evaluation, "active", active)

        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation_to_dict(evaluation)

    async def update_status(
        self, evaluation_id: int, status: str, count: int | None = None
    ) -> dict | None:
        """Update the processing status and teacher count of an evaluation."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if not evaluation:
            return None

        setattr(evaluation, "status", status)

        if count is not None:
            setattr(evaluation, "count", count)

        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation_to_dict(evaluation)

    async def delete(self, evaluation_id: int) -> None:
        """Delete an evaluation record by ID."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if evaluation:
            self.db.delete(evaluation)
            self.db.commit()

    async def get_teacher_comments(
        self, evaluation_id: int, teacher_id: int
    ) -> dict | None:
        """Return comments grouped by course for a teacher within an evaluation."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )
        if not evaluation:
            return None

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not teacher:
            return None

        from api.models.comment import CommentModel

        rows = (
            self.db.query(
                CommentModel.original_text,
                AcademicGroupModel.group_name,
                CourseModel.code.label("course_code"),
                CourseModel.name.label("course_name"),
            )
            .join(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(
                CommentModel.evaluation_id == evaluation_id,
                CommentModel.teacher_id == teacher_id,
            )
            .order_by(CourseModel.code, AcademicGroupModel.group_name)
            .all()
        )

        grouped: dict[tuple, dict] = {}
        for text, group_name, course_code, course_name in rows:
            key = (course_code, group_name)
            if key not in grouped:
                grouped[key] = {
                    "course_code": course_code,
                    "course_name": course_name,
                    "group_name": group_name,
                    "comments": [],
                }
            if text:
                grouped[key]["comments"].append(text)

        return {
            "teacher_id": teacher_id,
            "evaluation_id": evaluation_id,
            "courses": list(grouped.values()),
        }

    async def get_teacher_detail(
        self, evaluation_id: int, teacher_id: int
    ) -> dict | None:
        """Return per-course and per-dimension scores for a teacher within an evaluation."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )
        if not evaluation:
            return None

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not teacher:
            return None

        teacher_user = (
            self.db.query(UserModel).filter(UserModel.id == teacher.user_id).first()
            if teacher.user_id
            else None
        )

        score_rows = (
            self.db.query(EvaluationScoreModel, AcademicGroupModel, CourseModel)
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(
                EvaluationScoreModel.evaluation_id == evaluation_id,
                AcademicGroupModel.teacher_id == teacher_id,
            )
            .all()
        )

        if not score_rows:
            return None

        period = evaluation.academic_period
        courses = []
        accumulated: dict[str, list[float]] = {}

        for eval_score, group, course in score_rows:
            q_scores = (
                self.db.query(EvaluationQuestionScoreModel)
                .filter(
                    EvaluationQuestionScoreModel.evaluation_score_id == eval_score.id
                )
                .all()
            )

            group_q: dict[str, float] = {
                qs.question_code: float(qs.score) for qs in q_scores
            }

            for code, score in group_q.items():
                accumulated.setdefault(code, []).append(score)

            group_dims = []
            for dim_name, codes in DIMENSION_MAP.items():
                dim_scores = [group_q[c] for c in codes if c in group_q]
                group_dims.append(
                    {
                        "dimension": dim_name,
                        "average": (
                            round(sum(dim_scores) / len(dim_scores), 2)
                            if dim_scores
                            else None
                        ),
                    }
                )

            courses.append(
                {
                    "course_code": course.code,
                    "course_name": course.name,
                    "group_name": group.group_name,
                    "respondent_count": eval_score.respondent_count or 0,
                    "overall_average": (
                        float(eval_score.overall_average)
                        if eval_score.overall_average
                        else None
                    ),
                    "dimensions": group_dims,
                }
            )

        overall_dims = []
        for dim_name, codes in DIMENSION_MAP.items():
            dim_scores = [
                s for c in codes for s in accumulated.get(c, [])
            ]
            overall_dims.append(
                {
                    "dimension": dim_name,
                    "average": (
                        round(sum(dim_scores) / len(dim_scores), 2)
                        if dim_scores
                        else None
                    ),
                }
            )

        all_avgs = [c["overall_average"] for c in courses if c["overall_average"] is not None]
        overall_avg = round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else None

        return {
            "teacher_id": teacher_id,
            "institutional_code": teacher.institutional_code,
            "name": teacher_user.name if teacher_user else None,
            "contract_type": teacher.contract_type,
            "evaluation_id": evaluation_id,
            "period_code": period.code if period else None,
            "period_name": period.name if period else None,
            "overall_average": overall_avg,
            "group_count": len(courses),
            "courses": courses,
            "dimensions": overall_dims,
        }

    async def get_summary(self, evaluation_id: int) -> dict | None:
        """Return aggregated statistics for an evaluation grouped by teacher."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if not evaluation:
            return None

        rows = (
            self.db.query(
                TeacherModel.id,
                TeacherModel.institutional_code,
                TeacherModel.contract_type,
                UserModel.name,
                func.count(EvaluationScoreModel.id).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("teacher_avg"),
            )
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(TeacherModel, AcademicGroupModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .group_by(
                TeacherModel.id,
                TeacherModel.institutional_code,
                TeacherModel.contract_type,
                UserModel.name,
            )
            .order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .all()
        )

        dept_avg = (
            self.db.query(func.avg(EvaluationScoreModel.overall_average))
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .scalar()
        )

        ranking = [
            {
                "rank": idx + 1,
                "teacher_id": row.id,
                "institutional_code": row.institutional_code,
                "name": row.name,
                "contract_type": row.contract_type,
                "group_count": row.group_count,
                "overall_average": float(row.teacher_avg) if row.teacher_avg else None,
            }
            for idx, row in enumerate(rows)
        ]

        period = evaluation.academic_period

        return {
            "evaluation_id": evaluation_id,
            "period_code": period.code if period else None,
            "period_name": period.name if period else None,
            "department_average": float(dept_avg) if dept_avg else None,
            "teacher_count": len(ranking),
            "best_teacher": ranking[0] if ranking else None,
            "worst_teacher": ranking[-1] if ranking else None,
            "ranking": ranking,
        }


def get_evaluations_repository(db: Annotated[Session, Depends(get_db)]):
    """Get evaluations repository"""

    return EvaluationsRepository(db)
