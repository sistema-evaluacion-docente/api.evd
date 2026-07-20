"""
Academic periods controller
"""

from fastapi.param_functions import Depends

from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.evaluations import (
    EvaluationsRepository,
    get_evaluations_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodStatusUpdate,
    AcademicPeriodUpdate,
)
from api.schemas.audit import AuditCreate


class AcademicPeriodsController:
    """Academic periods controller"""

    def __init__(
        self,
        repository: AcademicPeriodsRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
        evaluations_repository: EvaluationsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository
        self.evaluations_repository = evaluations_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = self.users_repository.get_by_uid(current_user.uid)
        return user.id if user else None

    async def create(self, data: AcademicPeriodCreate, current_user) -> dict | None:
        """Create a new academic period."""

        existing = await self.repository.get_by_code(data.code)

        if existing:
            raise ValueError(
                f"An academic period with code '{data.code}' already exists"
            )

        period = await self.repository.create(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_periods",
                operation="CREATE",
                element=f"AcademicPeriod {period.get('id')}",
                description=f"Se creó el período académico {data.code} (nombre: {data.name}, inicio: {data.start_date}, fin: {data.end_date})",
                created_at=None,
            )
        )

        return period

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict | None:
        """Get all academic periods with pagination and optional search."""

        try:
            return await self.repository.get_all(search=search, page=page, limit=limit)
        except ValueError as e:
            print(e)
            return None

    async def get_by_id(self, period_id: int) -> dict | None:
        """Get an academic period by ID."""

        return await self.repository.get_by_id(period_id)

    async def update(
        self, period_id: int, data: AcademicPeriodUpdate, current_user
    ) -> dict | None:
        """Update an academic period."""

        period = await self.repository.get_by_id(period_id)

        if not period:
            return None

        updated = await self.repository.update(period_id, data)

        changes = []
        for field in (
            "name",
            "start_date",
            "end_date",
            "evaluation_end_date",
            "final_evaluation_date",
        ):
            new_val = getattr(data, field, None)
            if new_val is not None and new_val != period.get(field):
                old_val = period.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")
        desc = "Se actualizó el período académico #" + str(period_id)
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"
        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_periods",
                operation="UPDATE",
                element=f"AcademicPeriod {period_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated

    async def activate(self, period_id: int, current_user) -> dict | None:
        """Activate an academic period, deactivating any currently active one."""

        period = await self.repository.get_by_id(period_id)

        if not period:
            return None

        activated = await self.repository.set_active(period_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_periods",
                operation="ACTIVATE",
                element=f"AcademicPeriod {period_id}",
                description=f"Se activó el período académico {period.get('code', '')} (estaba inactivo)",
                created_at=None,
            )
        )

        return activated

    async def close(self, period_id: int, current_user) -> dict | None:
        """Close an academic period."""

        period = await self.repository.get_by_id(period_id)

        if not period:
            return None

        if not period.get("active"):
            raise ValueError("Only the active period can be closed")

        closed = await self.repository.close(period_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_periods",
                operation="CLOSE",
                element=f"AcademicPeriod {period_id}",
                description=f"Se cerró el período académico {period.get('code', '')} (estaba activo)",
                created_at=None,
            )
        )

        return closed

    async def update_status(
        self,
        period_id: int,
        data: AcademicPeriodStatusUpdate,
        current_user,
    ) -> dict | None:
        """Activate/deactivate an academic period."""

        period = await self.repository.get_by_id(period_id)

        if not period:
            return None

        updated = await self.repository.update_status(period_id, data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_periods",
                operation="UPDATE",
                element=f"AcademicPeriod {period_id}",
                description=f"Se cambió el estado del período académico {period.get('code', '')} de {'activo' if period.get('active') else 'inactivo'} a {'activo' if data.active else 'inactivo'}",
            )
        )

        return updated

    async def delete(self, period_id: int, current_user) -> bool:
        """Delete an academic period. Raises ValueError if period has evaluations."""

        period = await self.repository.get_by_id(period_id)

        if not period:
            return False

        has_evaluations = await self.evaluations_repository.has_evaluations_for_period(
            period_id
        )

        if has_evaluations:
            raise ValueError(
                f"No se puede eliminar el periodo '{period.get('code', '')}' porque tiene evaluaciones asociadas. "
                "Se recomienda desactivar el periodo en su lugar."
            )

        deleted = await self.repository.delete(period_id)

        if deleted:
            await self.audits_repository.create(
                AuditCreate(
                    user_id=await self._resolve_user_id(current_user),
                    table_name="academic_periods",
                    operation="DELETE",
                    element=f"AcademicPeriod {period_id}",
                    description=f"Se eliminó el período académico {period.get('code', '')} (nombre: {period.get('name', '')})",
                    created_at=None,
                )
            )

        return deleted


def get_academic_periods_controller(
    repository: AcademicPeriodsRepository = Depends(get_academic_periods_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    evaluations_repository: EvaluationsRepository = Depends(get_evaluations_repository),
):
    """Get academic periods controller"""

    return AcademicPeriodsController(
        repository, audits_repository, users_repository, evaluations_repository
    )
