"""
Evaluations repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.evaluation import EvaluationModel
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


def get_evaluations_repository(db: Annotated[Session, Depends(get_db)]):
    """Get evaluations repository"""

    return EvaluationsRepository(db)
