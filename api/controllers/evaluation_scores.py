"""
Evaluation scores controller
"""

from fastapi.param_functions import Depends

from api.repositories.evaluation_scores import (
    EvaluationScoresRepository,
    get_evaluation_scores_repository,
)


class EvaluationScoresController:
    """Evaluation scores controller"""

    def __init__(self, repository: EvaluationScoresRepository):
        self.repository = repository

    async def get_all(self) -> list[dict]:
        """Get all evaluation scores."""

        return await self.repository.get_all()

    async def get_by_id(self, score_id: int) -> dict | None:
        """Get an evaluation score by ID."""

        return await self.repository.get_by_id(score_id)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all scores for a given evaluation."""

        return await self.repository.get_by_evaluation(evaluation_id)

    async def get_by_evaluation_paginated(
        self,
        evaluation_id: int,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ) -> dict:
        """Get scores for a given evaluation with pagination and search."""

        return await self.repository.get_by_evaluation_paginated(
            evaluation_id,
            page=page,
            limit=limit,
            search=search,
        )


def get_evaluation_scores_controller(
    repository: EvaluationScoresRepository = Depends(get_evaluation_scores_repository),
):
    """Get evaluation scores controller"""

    return EvaluationScoresController(repository)
