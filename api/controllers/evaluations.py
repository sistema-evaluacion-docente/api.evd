"""
Evaluations controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.evaluations import EvaluationsRepository, get_evaluations_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate


class EvaluationsController:
    """Evaluations controller"""

    def __init__(
        self,
        repository: EvaluationsRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = await self.users_repository.get_by_uid(current_user.uid)
        return user["id"] if user else None

    async def get_all(
        self,
        period_id: int | None = None,
        department_id: int | None = None,
    ) -> list[dict]:
        """Get all evaluations with optional filters."""

        return await self.repository.get_all(
            period_id=period_id, department_id=department_id
        )

    async def get_by_id(self, evaluation_id: int) -> dict | None:
        """Get an evaluation by ID."""

        return await self.repository.get_by_id(evaluation_id)

    async def get_teacher_detail(
        self, evaluation_id: int, teacher_id: int
    ) -> dict | None:
        """Get per-course and per-dimension detail for a teacher in an evaluation."""

        return await self.repository.get_teacher_detail(evaluation_id, teacher_id)

    async def get_summary(self, evaluation_id: int) -> dict | None:
        """Get aggregated statistics for an evaluation."""

        return await self.repository.get_summary(evaluation_id)

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
                user_id=await self._resolve_user_id(current_user),
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
    users_repository: UsersRepository = Depends(get_users_repository),
):
    """Get evaluations controller"""

    return EvaluationsController(repository, audits_repository, users_repository)
