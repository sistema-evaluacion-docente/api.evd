"""
Improvement plans controller (Plan de Seguimiento Docente)
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.improvement_plans import (
    ImprovementPlansRepository,
    get_improvement_plans_repository,
)
from api.repositories.settings import SettingsRepository, get_settings_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.improvement_plan import (
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanUpdate,
)
from api.utils.improvement_suggestions import build_indicator_catalog

THRESHOLD_KEY = "improvement_plan.score_threshold"
DEFAULT_THRESHOLD = 3.5


class ImprovementPlansController:
    """Improvement plans controller"""

    def __init__(
        self,
        repository: ImprovementPlansRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
        settings_repository: SettingsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository
        self.settings_repository = settings_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        if isinstance(current_user, dict):
            return current_user.get("id")

        user = await self.users_repository.get_by_uid(current_user.uid)

        return user["id"] if user else None

    async def _get_threshold(self) -> float:
        setting = await self.settings_repository.get_by_key(THRESHOLD_KEY)
        if setting and setting.get("value"):
            try:
                return float(setting["value"])
            except (TypeError, ValueError):
                return DEFAULT_THRESHOLD
        return DEFAULT_THRESHOLD

    async def create(self, data: ImprovementPlanCreate, current_user) -> dict:
        """Create a new improvement plan."""

        user_id = await self._resolve_user_id(current_user)
        plan = await self.repository.create(data, created_by=user_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=user_id,
                table_name="improvement_plans",
                operation="CREATE",
                element=f"ImprovementPlan {plan.get('id')}",
                description=(
                    f"Se creó el plan de seguimiento '{data.title}' para el docente "
                    f"#{data.teacher_id} con {len(data.items)} ítem(s)"
                ),
                created_at=None,
            )
        )

        return plan

    async def get_all(
        self,
        department_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """List plans with filters and pagination."""

        return await self.repository.get_all(
            department_id=department_id,
            period_id=period_id,
            status=status,
            search=search,
            page=page,
            limit=limit,
        )

    async def get_by_id(self, plan_id: int) -> dict | None:
        """Get a plan by id."""

        return await self.repository.get_by_id(plan_id)

    async def update(
        self, plan_id: int, data: ImprovementPlanUpdate, current_user
    ) -> dict | None:
        """Update a plan and its items."""

        existing = await self.repository.get_by_id(plan_id)
        if not existing:
            return None

        updated = await self.repository.update(plan_id, data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="improvement_plans",
                operation="UPDATE",
                element=f"ImprovementPlan {plan_id}",
                description=f"Se actualizó el plan de seguimiento #{plan_id}",
                created_at=None,
            )
        )

        return updated

    async def close(
        self, plan_id: int, data: ImprovementPlanClose, current_user
    ) -> dict | None:
        """Close a plan with a result."""

        existing = await self.repository.get_by_id(plan_id)
        if not existing:
            return None

        closed = await self.repository.close(
            plan_id, data.result.value, data.reason
        )

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="improvement_plans",
                operation="CLOSE",
                element=f"ImprovementPlan {plan_id}",
                description=(
                    f"Se cerró el plan #{plan_id} con resultado {data.result.value}"
                    + (f": {data.reason}" if data.reason else "")
                ),
                created_at=None,
            )
        )

        return closed

    async def evaluate(self, plan_id: int, current_user) -> dict | None:
        """Recompute plan compliance against the verification period."""

        existing = await self.repository.get_by_id(plan_id)
        if not existing:
            return None

        evaluated = await self.repository.evaluate(
            plan_id, threshold=await self._get_threshold()
        )

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="improvement_plans",
                operation="EVALUATE",
                element=f"ImprovementPlan {plan_id}",
                description=(
                    f"Se recalculó el cumplimiento del plan #{plan_id}. "
                    f"Sugerencia: {evaluated.get('suggested_result') if evaluated else None}"
                ),
                created_at=None,
            )
        )

        return evaluated

    async def get_at_risk(
        self, period_id: int, department_id: int
    ) -> list[dict]:
        """Teachers below threshold without a plan for the given period."""

        threshold = await self._get_threshold()

        return await self.repository.get_at_risk(
            department_id=department_id,
            period_id=period_id,
            threshold=threshold,
        )

    async def get_candidates(
        self,
        period_id: int,
        department_id: int,
        only_at_risk: bool = False,
        search: str | None = None,
    ) -> dict:
        """Teachers eligible for a plan with their indicator averages."""

        threshold = await self._get_threshold()

        teachers = await self.repository.get_candidates(
            department_id=department_id,
            period_id=period_id,
            threshold=threshold,
            only_at_risk=only_at_risk,
            search=search,
        )

        return {"threshold": threshold, "teachers": teachers}

    async def get_indicators(self) -> dict:
        """Catalogue of selectable indicators for a plan item (compromiso)."""

        return {
            "threshold": await self._get_threshold(),
            **build_indicator_catalog(),
        }


def get_improvement_plans_controller(
    repository: ImprovementPlansRepository = Depends(
        get_improvement_plans_repository
    ),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    settings_repository: SettingsRepository = Depends(get_settings_repository),
):
    """Get improvement plans controller"""

    return ImprovementPlansController(
        repository, audits_repository, users_repository, settings_repository
    )
