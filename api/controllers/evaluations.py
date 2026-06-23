"""
Evaluations controller
"""

from fastapi.param_functions import Depends

from api.repositories.evaluations import EvaluationsRepository, get_evaluations_repository


class EvaluationsController:
    """Evaluations controller"""

    def __init__(self, repository: EvaluationsRepository):
        self.repository = repository

    async def get_all(self) -> list[dict]:
        """Get all evaluations."""

        return await self.repository.get_all()

    async def get_by_id(self, evaluation_id: int) -> dict | None:
        """Get an evaluation by ID."""

        return await self.repository.get_by_id(evaluation_id)


def get_evaluations_controller(
    repository: EvaluationsRepository = Depends(get_evaluations_repository),
):
    """Get evaluations controller"""

    return EvaluationsController(repository)
