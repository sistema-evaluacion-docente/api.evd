"""
Evaluation question scores repository
"""

from decimal import Decimal
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.serializers.evaluation_question_scores import evaluation_question_score_to_dict


class EvaluationQuestionScoresRepository:
    """Evaluation question scores repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        evaluation_score_id: int,
        question_code: str,
        score: Decimal,
    ) -> dict:
        """Create a new evaluation question score."""

        question_score = EvaluationQuestionScoreModel(
            evaluation_score_id=evaluation_score_id,
            question_code=question_code,
            score=score,
        )

        self.db.add(question_score)
        self.db.commit()
        self.db.refresh(question_score)

        return evaluation_question_score_to_dict(question_score)

    async def get_by_evaluation_score(self, evaluation_score_id: int) -> list[dict]:
        """Get all question scores for a given evaluation score."""

        question_scores = (
            self.db.query(EvaluationQuestionScoreModel)
            .filter(
                EvaluationQuestionScoreModel.evaluation_score_id == evaluation_score_id
            )
            .order_by(EvaluationQuestionScoreModel.question_code)
            .all()
        )

        return [evaluation_question_score_to_dict(qs) for qs in question_scores]

    async def get_by_id(self, question_score_id: int) -> dict | None:
        """Get an evaluation question score by ID."""

        question_score = (
            self.db.query(EvaluationQuestionScoreModel)
            .filter(EvaluationQuestionScoreModel.id == question_score_id)
            .first()
        )

        if not question_score:
            return None

        return evaluation_question_score_to_dict(question_score)


def get_evaluation_question_scores_repository(db: Annotated[Session, Depends(get_db)]):
    """Get evaluation question scores repository"""

    return EvaluationQuestionScoresRepository(db)
