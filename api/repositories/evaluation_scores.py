"""
Evaluation scores repository
"""

from decimal import Decimal
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.evaluation_score import EvaluationScoreModel
from api.serializers.evaluation_scores import evaluation_score_to_dict


class EvaluationScoresRepository:
    """Evaluation scores repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        evaluation_id: int,
        academic_group_id: int,
        respondent_count: int,
        overall_average: Decimal | None = None,
    ) -> dict:
        """Create a new evaluation score."""

        score = EvaluationScoreModel(
            evaluation_id=evaluation_id,
            academic_group_id=academic_group_id,
            respondent_count=respondent_count,
            overall_average=overall_average,
        )

        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)

        return evaluation_score_to_dict(score)

    async def get_all(self) -> list[dict]:
        """Get all evaluation scores."""

        scores = (
            self.db.query(EvaluationScoreModel)
            .order_by(EvaluationScoreModel.created_at.desc())
            .all()
        )

        return [evaluation_score_to_dict(s) for s in scores]

    async def get_by_id(self, score_id: int) -> dict | None:
        """Get an evaluation score by ID."""

        score = (
            self.db.query(EvaluationScoreModel)
            .filter(EvaluationScoreModel.id == score_id)
            .first()
        )

        if not score:
            return None

        return evaluation_score_to_dict(score)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all scores for a given evaluation."""

        scores = (
            self.db.query(EvaluationScoreModel)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .all()
        )

        return [evaluation_score_to_dict(s) for s in scores]

    async def get_by_evaluation_and_group(
        self, evaluation_id: int, academic_group_id: int
    ) -> dict | None:
        """Get a score by evaluation and academic group — used for duplicate detection."""

        score = (
            self.db.query(EvaluationScoreModel)
            .filter(
                EvaluationScoreModel.evaluation_id == evaluation_id,
                EvaluationScoreModel.academic_group_id == academic_group_id,
            )
            .first()
        )

        if not score:
            return None

        return evaluation_score_to_dict(score)


def get_evaluation_scores_repository(db: Annotated[Session, Depends(get_db)]):
    """Get evaluation scores repository"""

    return EvaluationScoresRepository(db)
