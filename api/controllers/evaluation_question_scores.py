"""
Evaluation question scores controller
"""

from fastapi.param_functions import Depends

from api.repositories.evaluation_question_scores import (
    EvaluationQuestionScoresRepository,
    get_evaluation_question_scores_repository,
)


class EvaluationQuestionScoresController:
    """Evaluation question scores controller"""

    def __init__(self, repository: EvaluationQuestionScoresRepository):
        self.repository = repository

    async def get_by_id(self, question_score_id: int) -> dict | None:
        """Get an evaluation question score by ID."""

        return await self.repository.get_by_id(question_score_id)

    async def get_by_evaluation_score(self, evaluation_score_id: int) -> list[dict]:
        """Get all question scores for a given evaluation score."""

        return await self.repository.get_by_evaluation_score(evaluation_score_id)


def get_evaluation_question_scores_controller(
    repository: EvaluationQuestionScoresRepository = Depends(
        get_evaluation_question_scores_repository
    ),
):
    """Get evaluation question scores controller"""

    return EvaluationQuestionScoresController(repository)
