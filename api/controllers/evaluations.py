"""
Evaluations controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.evaluations import EvaluationsRepository, get_evaluations_repository
from api.schemas.audit import AuditCreate


class EvaluationsController:
    """Evaluations controller"""

    def __init__(
        self,
        repository: EvaluationsRepository,
        audits_repository: AuditsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository

    async def get_all(self) -> list[dict]:
        """Get all evaluations."""

        return await self.repository.get_all()

    async def get_by_id(self, evaluation_id: int) -> dict | None:
        """Get an evaluation by ID."""

        return await self.repository.get_by_id(evaluation_id)

    async def update_status(
        self, evaluation_id: int, active: bool, current_user
    ) -> dict | None:
        """Activate or deactivate an evaluation."""

        evaluation = await self.repository.get_by_id(evaluation_id)

        if not evaluation:
            return None

        updated = await self.repository.update_active_status(evaluation_id, active)

        operation = "ACTIVATE" if active else "DEACTIVATE"

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="evaluations",
                operation=operation,
                element=f"Evaluation {evaluation_id}",
                description=f"Se {'activó' if active else 'desactivó'} la evaluación {evaluation_id} del período {evaluation.get('academic_period_code', '')}",
            )
        )

        return updated


def get_evaluations_controller(
    repository: EvaluationsRepository = Depends(get_evaluations_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
):
    """Get evaluations controller"""

    return EvaluationsController(repository, audits_repository)
