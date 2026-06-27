"""
Evaluations repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.serializers.evaluations import evaluation_to_dict


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

    async def get_all(self) -> list[dict]:
        """Get all evaluations ordered by creation date descending."""

        evaluations = (
            self.db.query(EvaluationModel)
            .order_by(EvaluationModel.created_at.desc())
            .all()
        )

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
