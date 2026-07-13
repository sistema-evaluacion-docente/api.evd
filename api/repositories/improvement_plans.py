"""
Improvement plans repository (Plan de Seguimiento Docente)
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_period import AcademicPeriodModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_item import ImprovementPlanItemModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.stats import StatsRepository
from api.schemas.improvement_plan import (
    ImprovementPlanCreate,
    ImprovementPlanUpdate,
)
from api.serializers.improvement_plans import improvement_plan_to_dict
from api.utils.improvement_suggestions import suggest_actions

CHECKPOINT_STAGES = ["INICIO", "MITAD", "SEMANA_16"]

CLOSE_RESULT_TO_STATUS = {
    "CUMPLIDO": "CERRADO_CUMPLIDO",
    "NO_CUMPLIDO": "CERRADO_NO_CUMPLIDO",
    "MANUAL": "CERRADO_MANUAL",
}


class ImprovementPlansRepository:
    """Improvement plans repository"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _next_period_code(code: str) -> str | None:
        """Get the following academic period code from a code like '2025-1'."""

        parts = code.split("-")
        if len(parts) != 2:
            return None

        year = int(parts[0])
        semester = int(parts[1])

        if semester == 1:
            return f"{year}-2"
        return f"{year + 1}-1"

    def _period_code(self, period_id: int | None) -> str | None:
        if not period_id:
            return None
        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )
        return period.code if period else None

    def _period_by_code(self, code: str) -> AcademicPeriodModel | None:
        return (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.code == code)
            .first()
        )

    def _teacher_info(self, teacher_id: int) -> tuple[str | None, str | None]:
        """Return (name, avatar_url) for a teacher via its linked user."""

        row = (
            self.db.query(UserModel.name, UserModel.avatar_url)
            .join(TeacherModel, TeacherModel.user_id == UserModel.id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not row:
            return None, None
        return row[0], row[1]

    def _load(self, plan_id: int) -> ImprovementPlanModel | None:
        return (
            self.db.query(ImprovementPlanModel)
            .filter(ImprovementPlanModel.id == plan_id)
            .first()
        )

    def _enrich(
        self, plan: ImprovementPlanModel, suggested_result: str | None = None
    ) -> dict:
        name, avatar = self._teacher_info(plan.teacher_id)
        return improvement_plan_to_dict(
            plan,
            teacher_name=name,
            teacher_avatar_url=avatar,
            origin_period_code=self._period_code(plan.origin_period_id),
            verification_period_code=self._period_code(plan.verification_period_id),
            suggested_result=suggested_result,
        )

    async def has_plan_for(self, teacher_id: int, origin_period_id: int) -> bool:
        """Whether a plan already exists for this teacher and origin period."""

        return (
            self.db.query(ImprovementPlanModel.id)
            .filter(
                ImprovementPlanModel.teacher_id == teacher_id,
                ImprovementPlanModel.origin_period_id == origin_period_id,
            )
            .first()
            is not None
        )

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    async def create(
        self, data: ImprovementPlanCreate, created_by: int | None = None
    ) -> dict:
        """Create a plan with its items and the three follow-up checkpoints."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == data.teacher_id)
            .first()
        )
        department_id = teacher.department_id if teacher else None

        verification_period_id = data.verification_period_id
        if verification_period_id is None:
            origin_code = self._period_code(data.origin_period_id)
            if origin_code:
                next_code = self._next_period_code(origin_code)
                if next_code:
                    next_period = self._period_by_code(next_code)
                    if next_period:
                        verification_period_id = next_period.id

        plan = ImprovementPlanModel(
            teacher_id=data.teacher_id,
            department_id=department_id,
            origin_period_id=data.origin_period_id,
            verification_period_id=verification_period_id,
            title=data.title,
            description=data.description,
            status="EN_SEGUIMIENTO",
            start_date=data.start_date,
            end_date=data.end_date,
            created_by=created_by,
        )

        for index, item in enumerate(data.items):
            plan.items.append(
                ImprovementPlanItemModel(
                    description=item.description,
                    target_type=item.target_type.value,
                    target_ref=item.target_ref,
                    baseline_value=item.baseline_value,
                    target_value=item.target_value,
                    status=item.status.value if item.status else "PENDIENTE",
                    order=item.order if item.order is not None else index,
                )
            )

        for stage in CHECKPOINT_STAGES:
            plan.checkpoints.append(
                ImprovementPlanCheckpointModel(stage=stage, status="PENDIENTE")
            )

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    async def get_all(
        self,
        department_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get paginated plans with optional filters."""

        query = self.db.query(ImprovementPlanModel)

        if department_id is not None:
            query = query.filter(ImprovementPlanModel.department_id == department_id)
        if period_id is not None:
            query = query.filter(
                or_(
                    ImprovementPlanModel.origin_period_id == period_id,
                    ImprovementPlanModel.verification_period_id == period_id,
                )
            )
        if status:
            query = query.filter(ImprovementPlanModel.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = (
                query.join(TeacherModel, TeacherModel.id == ImprovementPlanModel.teacher_id)
                .join(UserModel, UserModel.id == TeacherModel.user_id)
                .filter(
                    or_(
                        ImprovementPlanModel.title.ilike(term),
                        UserModel.name.ilike(term),
                    )
                )
            )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        plans = (
            query.order_by(ImprovementPlanModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [self._enrich(plan) for plan in plans],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, plan_id: int) -> dict | None:
        """Get a single plan with items and checkpoints."""

        plan = self._load(plan_id)
        if not plan:
            return None
        return self._enrich(plan)

    async def update(self, plan_id: int, data: ImprovementPlanUpdate) -> dict | None:
        """Update plan fields and, if provided, replace its item list."""

        plan = self._load(plan_id)
        if not plan:
            return None

        payload = data.model_dump(exclude_unset=True)
        payload.pop("items", None)

        for field, value in payload.items():
            setattr(plan, field, value)

        if data.items is not None:
            existing = {item.id: item for item in plan.items}
            incoming_ids: set[int] = set()

            for index, incoming in enumerate(data.items):
                if incoming.id and incoming.id in existing:
                    item = existing[incoming.id]
                    item.description = incoming.description
                    item.target_type = incoming.target_type.value
                    item.target_ref = incoming.target_ref
                    item.baseline_value = incoming.baseline_value
                    item.target_value = incoming.target_value
                    if incoming.status:
                        item.status = incoming.status.value
                    item.order = (
                        incoming.order if incoming.order is not None else index
                    )
                    incoming_ids.add(incoming.id)
                else:
                    plan.items.append(
                        ImprovementPlanItemModel(
                            description=incoming.description,
                            target_type=incoming.target_type.value,
                            target_ref=incoming.target_ref,
                            baseline_value=incoming.baseline_value,
                            target_value=incoming.target_value,
                            status=(
                                incoming.status.value
                                if incoming.status
                                else "PENDIENTE"
                            ),
                            order=(
                                incoming.order
                                if incoming.order is not None
                                else index
                            ),
                        )
                    )

            for item_id, item in existing.items():
                if item_id not in incoming_ids:
                    self.db.delete(item)

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    async def close(
        self, plan_id: int, result: str, reason: str | None = None
    ) -> dict | None:
        """Close a plan with the given result (CUMPLIDO / NO_CUMPLIDO / MANUAL)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        plan.status = CLOSE_RESULT_TO_STATUS.get(result, "CERRADO_MANUAL")
        plan.close_reason = reason
        plan.closed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    # ------------------------------------------------------------------ #
    # Compliance verification against the verification period
    # ------------------------------------------------------------------ #
    async def evaluate(self, plan_id: int) -> dict | None:
        """Recompute item results against the verification period and suggest
        an aggregated result. Does NOT close the plan (director confirms)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        stats = StatsRepository(self.db)

        # Resolve verification period (auto from origin if missing).
        verification_period_id = plan.verification_period_id
        if verification_period_id is None:
            origin_code = self._period_code(plan.origin_period_id)
            next_code = self._next_period_code(origin_code) if origin_code else None
            next_period = self._period_by_code(next_code) if next_code else None
            if next_period:
                verification_period_id = next_period.id
                plan.verification_period_id = next_period.id

        if verification_period_id is None:
            # Nothing to verify against yet.
            return self._enrich(plan)

        overall = await stats.get_teacher_average_with_previous(
            plan.teacher_id, verification_period_id
        )
        overall_avg = overall.get("overall_average") if overall else None

        dim_data = await stats.get_teacher_dimension_averages(
            plan.teacher_id, verification_period_id
        )
        dim_by_name: dict[str, float | None] = {}
        if dim_data:
            for d in dim_data.get("dimensions", []):
                dim_by_name[d["dimension"]] = d["average"]

        measurable = 0
        fulfilled = 0

        for item in plan.items:
            result_value: float | None = None

            if item.target_type == "OVERALL_AVERAGE":
                result_value = overall_avg
            elif item.target_type == "DIMENSION" and item.target_ref:
                result_value = dim_by_name.get(item.target_ref)

            if item.target_type in ("OVERALL_AVERAGE", "DIMENSION"):
                measurable += 1
                item.result_value = result_value
                target = float(item.target_value) if item.target_value else None
                if result_value is not None and target is not None:
                    if result_value >= target:
                        item.status = "CUMPLIDO"
                        fulfilled += 1
                    else:
                        item.status = "NO_CUMPLIDO"

        suggested_result = None
        if measurable > 0:
            suggested_result = (
                "CUMPLIDO" if fulfilled == measurable else "NO_CUMPLIDO"
            )
            plan.status = "RESULTADO_DISPONIBLE"

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan, suggested_result=suggested_result)

    # ------------------------------------------------------------------ #
    # At-risk detection (auto-detección + sugerencias)
    # ------------------------------------------------------------------ #
    async def get_at_risk(
        self,
        department_id: int,
        period_id: int,
        threshold: float,
    ) -> list[dict]:
        """Teachers in the department below threshold in the period that do not
        yet have a plan for that period, with weak dimensions + suggestions."""

        stats = StatsRepository(self.db)

        ranking = await stats.get_teacher_ranking_paginated(
            academic_period_id=period_id,
            department_id=department_id,
            page=1,
            limit=1000,
            sort="asc",
        )

        result: list[dict] = []

        for teacher in ranking.get("teachers", []):
            avg = teacher.get("overall_average")
            if avg is None or avg >= threshold:
                continue

            teacher_id = teacher["teacher_id"]

            if await self.has_plan_for(teacher_id, period_id):
                continue

            dim_data = await stats.get_teacher_dimension_averages(
                teacher_id, period_id
            )
            weak_dimensions = []
            if dim_data:
                for d in dim_data.get("dimensions", []):
                    d_avg = d.get("average")
                    if d_avg is not None and d_avg < threshold:
                        weak_dimensions.append(
                            {
                                "dimension": d["dimension"],
                                "average": d_avg,
                                "suggestions": suggest_actions(
                                    "DIMENSION", d["dimension"]
                                ),
                            }
                        )

            result.append(
                {
                    "teacher_id": teacher_id,
                    "name": teacher.get("name"),
                    "avatar_url": teacher.get("avatar_url"),
                    "institutional_code": teacher.get("institutional_code"),
                    "overall_average": avg,
                    "weak_dimensions": weak_dimensions,
                    "overall_suggestions": suggest_actions("OVERALL_AVERAGE"),
                }
            )

        return result


def get_improvement_plans_repository(db: Annotated[Session, Depends(get_db)]):
    """Get improvement plans repository"""

    return ImprovementPlansRepository(db)
