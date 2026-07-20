"""Service for academic period-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ValidationError,
)
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.evaluations import EvaluationsRepository
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodFilters,
    AcademicPeriodUpdate,
)
from api.schemas.pagination import build_paginated_response
from api.serializers.academic_periods import academic_period_to_dict
from api.services.audit_service import AuditService


class AcademicPeriodService:
    """Service for academic period-related business operations."""

    def __init__(
        self,
        academic_periods_repository: AcademicPeriodsRepository,
        evaluations_repository: EvaluationsRepository,
        audit_service: AuditService,
    ):
        self.academic_periods_repository = academic_periods_repository
        self.evaluations_repository = evaluations_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: AcademicPeriodFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all academic periods based on filters and pagination."""

        periods, total = self.academic_periods_repository.search(filters, pagination)
        items = [academic_period_to_dict(period) for period in periods]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, period_id: int) -> dict | None:
        """Retrieve an academic period by ID."""

        period = self.academic_periods_repository.get(period_id)

        if not period:
            return None

        return academic_period_to_dict(period)

    async def create(self, data: AcademicPeriodCreate, current_user: dict) -> dict:
        """Create a new academic period, rejecting duplicate codes and date overlaps."""

        existing = self.academic_periods_repository.get_by_code(data.code)

        if existing:
            raise ResourceAlreadyExistsError("academic_period", "code", data.code)

        if data.start_date and data.end_date:
            if self.academic_periods_repository.overlaps_with(
                data.start_date, data.end_date
            ):
                raise ValidationError(
                    "El rango de fechas se solapa con otro periodo académico existente"
                )

        period = self.academic_periods_repository.create_period(data.model_dump())
        self.academic_periods_repository.db.commit()
        self.academic_periods_repository.db.refresh(period)

        result = academic_period_to_dict(period)

        await self.audit_service.log(
            action="CREATE",
            entity_name="academic_periods",
            entity_id=period.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el período académico {data.code} "
                f"(nombre: {data.name}, inicio: {data.start_date}, fin: {data.end_date})"
            ),
        )

        return result

    async def update(
        self, period_id: int, data: AcademicPeriodUpdate, current_user: dict
    ) -> dict | None:
        """Update an academic period's fields."""

        period = self.academic_periods_repository.get(period_id)

        if not period:
            return None

        old_data = academic_period_to_dict(period)
        payload = data.model_dump(exclude_unset=True)

        if data.start_date and data.end_date:
            if self.academic_periods_repository.overlaps_with(
                data.start_date, data.end_date, exclude_id=period_id
            ):
                raise ValidationError(
                    "El rango de fechas se solapa con otro periodo académico existente"
                )

        updated = self.academic_periods_repository.update_period(period, payload)
        result = academic_period_to_dict(updated)

        changes = []
        for field in (
            "name",
            "start_date",
            "end_date",
            "evaluation_end_date",
            "final_evaluation_date",
        ):
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = "Se actualizó el período académico"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="academic_periods",
            entity_id=period_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return result

    async def activate(self, period_id: int, current_user: dict) -> dict | None:
        """Activate an academic period."""

        period = self.academic_periods_repository.get(period_id)

        if not period:
            return None

        activated = self.academic_periods_repository.activate_period(period)
        result = academic_period_to_dict(activated)

        await self.audit_service.log(
            action="UPDATE",
            entity_name="academic_periods",
            entity_id=period_id,
            actor_id=current_user.get("id"),
            description=f"Se activó el período académico {period.code}",
        )

        return result

    async def close(self, period_id: int, current_user: dict) -> dict | None:
        """Close (deactivate) an academic period."""

        period = self.academic_periods_repository.get(period_id)

        if not period:
            return None

        closed = self.academic_periods_repository.close_period(period)
        result = academic_period_to_dict(closed)

        await self.audit_service.log(
            action="UPDATE",
            entity_name="academic_periods",
            entity_id=period_id,
            actor_id=current_user.get("id"),
            description=f"Se cerró el período académico {period.code}",
        )

        return result

    async def delete(self, period_id: int, current_user: dict) -> dict | None:
        """Delete an academic period, rejecting if it has evaluations."""

        period = self.academic_periods_repository.get(period_id)

        if not period:
            return None

        has_evaluations = await self.evaluations_repository.has_evaluations_for_period(
            period_id
        )

        if has_evaluations:
            raise ValidationError(
                f"No se puede eliminar el periodo '{period.code}' porque tiene evaluaciones asociadas. "
                "Se recomienda desactivar el periodo en su lugar."
            )

        old_data = academic_period_to_dict(period)
        self.academic_periods_repository.delete_period(period_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="academic_periods",
            entity_id=period_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó el período académico {old_data.get('code')} "
                f"(nombre: {old_data.get('name')})"
            ),
        )

        return old_data
