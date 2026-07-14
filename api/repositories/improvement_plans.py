"""
Improvement plans repository (Plan de Seguimiento Docente)
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_evidence import ImprovementPlanEvidenceModel
from api.models.improvement_plan_item import ImprovementPlanItemModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.stats import StatsRepository
from api.schemas.improvement_plan import (
    ImprovementPlanCreate,
    ImprovementPlanUpdate,
)
from api.serializers.improvement_plans import improvement_plan_to_dict
from api.utils.dimensions import DIMENSION_MAP, QUESTION_TEXT
from api.utils.improvement_suggestions import suggest_actions

CHECKPOINT_STAGES = ["INICIO", "MITAD", "SEMANA_16"]

MEASURABLE_TARGET_TYPES = ("OVERALL_AVERAGE", "DIMENSION", "QUESTION")

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

        uploader_ids = {e.uploaded_by for e in plan.evidences if e.uploaded_by}
        uploader_names: dict[int, str] = {}
        if uploader_ids:
            rows = (
                self.db.query(UserModel.id, UserModel.name)
                .filter(UserModel.id.in_(uploader_ids))
                .all()
            )
            uploader_names = {row[0]: row[1] for row in rows}

        return improvement_plan_to_dict(
            plan,
            teacher_name=name,
            teacher_avatar_url=avatar,
            origin_period_code=self._period_code(plan.origin_period_id),
            verification_period_code=self._period_code(plan.verification_period_id),
            suggested_result=suggested_result,
            evidence_uploader_names=uploader_names,
        )

    def get_teacher_user_id(self, teacher_id: int) -> int | None:
        """User id linked to a teacher (to check a DOCENTE owns the plan)."""

        row = (
            self.db.query(TeacherModel.user_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        return row[0] if row else None

    def get_teacher_by_user_id(self, user_id: int) -> TeacherModel | None:
        """Teacher record linked to a user, if any."""

        return (
            self.db.query(TeacherModel)
            .filter(TeacherModel.user_id == user_id)
            .first()
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

    def _teachers_with_plan(
        self, teacher_ids: list[int], origin_period_id: int
    ) -> set[int]:
        """Teachers from the list that already have a plan for the period."""

        if not teacher_ids:
            return set()

        rows = (
            self.db.query(ImprovementPlanModel.teacher_id)
            .filter(
                ImprovementPlanModel.teacher_id.in_(teacher_ids),
                ImprovementPlanModel.origin_period_id == origin_period_id,
            )
            .all()
        )

        return {row[0] for row in rows}

    # ------------------------------------------------------------------ #
    # Indicator averages (question = one item of the evaluation form)
    # ------------------------------------------------------------------ #
    def _question_averages(
        self, teacher_ids: list[int], period_id: int
    ) -> dict[int, dict[str, float]]:
        """Per-teacher, per-question averages for a period, in a single query."""

        if not teacher_ids:
            return {}

        rows = (
            self.db.query(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.teacher_id.in_(teacher_ids),
                EvaluationModel.academic_period_id == period_id,
            )
            .group_by(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
            )
            .all()
        )

        averages: dict[int, dict[str, float]] = {}
        for row in rows:
            averages.setdefault(row.teacher_id, {})[row.question_code] = round(
                float(row.avg_score), 2
            )

        return averages

    @staticmethod
    def _dimension_average(
        question_averages: dict[str, float], codes: list[str]
    ) -> float | None:
        scores = [question_averages[c] for c in codes if c in question_averages]

        return round(sum(scores) / len(scores), 2) if scores else None

    def _build_indicators(
        self, question_averages: dict[str, float], threshold: float
    ) -> list[dict]:
        """Every dimension with its own average and the average of each of its
        questions, flagged against the institutional threshold."""

        dimensions = []

        for dimension, codes in DIMENSION_MAP.items():
            average = self._dimension_average(question_averages, codes)
            questions = []

            for code in codes:
                q_average = question_averages.get(code)
                questions.append(
                    {
                        "target_type": "QUESTION",
                        "target_ref": code,
                        "code": code,
                        "text": QUESTION_TEXT.get(code, code),
                        "average": q_average,
                        "below_threshold": (
                            q_average is not None and q_average < threshold
                        ),
                        "suggestions": suggest_actions("QUESTION", code),
                    }
                )

            dimensions.append(
                {
                    "dimension": dimension,
                    "target_type": "DIMENSION",
                    "target_ref": dimension,
                    "average": average,
                    "below_threshold": average is not None and average < threshold,
                    "suggestions": suggest_actions("DIMENSION", dimension),
                    "questions": questions,
                }
            )

        return dimensions

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
        teacher_id: int | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get paginated plans with optional filters."""

        query = self.db.query(ImprovementPlanModel)

        if department_id is not None:
            query = query.filter(ImprovementPlanModel.department_id == department_id)
        if teacher_id is not None:
            query = query.filter(ImprovementPlanModel.teacher_id == teacher_id)
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

    async def get_by_teacher(self, teacher_id: int) -> list[dict]:
        """All plans of a teacher, newest first (for the teacher-facing view)."""

        plans = (
            self.db.query(ImprovementPlanModel)
            .filter(ImprovementPlanModel.teacher_id == teacher_id)
            .order_by(ImprovementPlanModel.created_at.desc())
            .all()
        )
        return [self._enrich(plan) for plan in plans]

    # ------------------------------------------------------------------ #
    # Acta de compromiso & evidences
    # ------------------------------------------------------------------ #
    async def set_acta(
        self,
        plan_id: int,
        file_url: str | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Attach/replace the acta PDF and/or update its description.

        Returns the enriched plan plus the previous file url (so the caller
        can remove the replaced file from disk)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        previous_file_url = None

        if file_url:
            previous_file_url = plan.acta_pdf_url
            plan.acta_pdf_url = file_url
            plan.acta_uploaded_at = datetime.now(timezone.utc)

        if description is not None:
            plan.acta_description = description.strip() or None

        self.db.commit()
        self.db.refresh(plan)

        return {
            "plan": self._enrich(plan),
            "previous_file_url": previous_file_url,
        }

    async def add_evidence(
        self,
        plan_id: int,
        file_url: str,
        description: str | None = None,
        item_id: int | None = None,
        uploaded_by: int | None = None,
    ) -> dict | None:
        """Attach an evidence PDF to the plan (optionally tied to an item)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        if item_id is not None and not any(i.id == item_id for i in plan.items):
            raise ValueError("El ítem indicado no pertenece a este plan")

        plan.evidences.append(
            ImprovementPlanEvidenceModel(
                item_id=item_id,
                uploaded_by=uploaded_by,
                description=(description.strip() or None) if description else None,
                file_url=file_url,
            )
        )

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    def get_evidence(
        self, plan_id: int, evidence_id: int
    ) -> ImprovementPlanEvidenceModel | None:
        return (
            self.db.query(ImprovementPlanEvidenceModel)
            .filter(
                ImprovementPlanEvidenceModel.id == evidence_id,
                ImprovementPlanEvidenceModel.plan_id == plan_id,
            )
            .first()
        )

    async def delete_evidence(self, plan_id: int, evidence_id: int) -> dict | None:
        """Delete an evidence. Returns the enriched plan and the removed file
        url so the caller can delete it from disk."""

        evidence = self.get_evidence(plan_id, evidence_id)
        if not evidence:
            return None

        file_url = evidence.file_url
        self.db.delete(evidence)
        self.db.commit()

        plan = self._load(plan_id)

        return {
            "plan": self._enrich(plan) if plan else None,
            "file_url": file_url,
        }

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
    async def evaluate(self, plan_id: int, threshold: float) -> dict | None:
        """Recompute item results against the verification period and suggest
        an aggregated result. Does NOT close the plan (director confirms).

        Items without an explicit ``target_value`` are verified against the
        institutional ``threshold``."""

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

        question_avgs = self._question_averages(
            [plan.teacher_id], verification_period_id
        ).get(plan.teacher_id, {})

        dim_by_name = {
            dimension: self._dimension_average(question_avgs, codes)
            for dimension, codes in DIMENSION_MAP.items()
        }

        measured = 0
        fulfilled = 0

        for item in plan.items:
            if item.target_type not in MEASURABLE_TARGET_TYPES:
                continue

            result_value: float | None = None

            if item.target_type == "OVERALL_AVERAGE":
                result_value = overall_avg
            elif item.target_type == "DIMENSION" and item.target_ref:
                result_value = dim_by_name.get(item.target_ref)
            elif item.target_type == "QUESTION" and item.target_ref:
                result_value = question_avgs.get(item.target_ref)

            item.result_value = result_value

            if result_value is None:
                # The verification period has no grades for this indicator yet:
                # leave the item as it is instead of failing it for missing data.
                continue

            target = (
                float(item.target_value)
                if item.target_value is not None
                else threshold
            )

            measured += 1

            if result_value >= target:
                item.status = "CUMPLIDO"
                fulfilled += 1
            else:
                item.status = "NO_CUMPLIDO"

        suggested_result = None
        if measured > 0:
            suggested_result = "CUMPLIDO" if fulfilled == measured else "NO_CUMPLIDO"
            plan.status = "RESULTADO_DISPONIBLE"

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan, suggested_result=suggested_result)

    async def get_evaluated_periods(self, department_id: int) -> list[dict]:
        """Periods whose grades are already loaded for the department, newest
        first.

        A plan's origin period is the one where the low performance was
        detected, so only periods with an uploaded evaluation can be chosen —
        the current academic period usually has no grades yet (they arrive at
        the start of the next one)."""

        rows = (
            self.db.query(
                AcademicPeriodModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .join(
                EvaluationModel,
                EvaluationModel.academic_period_id == AcademicPeriodModel.id,
            )
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.status == "COMPLETED",
                EvaluationModel.active.is_(True),
            )
            .distinct()
            .order_by(AcademicPeriodModel.code.desc())
            .all()
        )

        return [{"id": row.id, "code": row.code, "name": row.name} for row in rows]

    # ------------------------------------------------------------------ #
    # Candidates for a plan (auto-detección + sugerencias)
    # ------------------------------------------------------------------ #
    async def get_candidates(
        self,
        department_id: int,
        period_id: int,
        threshold: float,
        only_at_risk: bool = False,
        search: str | None = None,
    ) -> list[dict]:
        """Teachers of the department evaluated in the period, each with the
        average of every dimension and of every question of the form.

        A teacher can be below the threshold in a single question while keeping
        a healthy overall average, so by default the whole department is
        returned and the caller decides. ``only_at_risk`` narrows the list to
        teachers below the threshold that have no plan yet for the period
        (auto-detection for the dashboard)."""

        stats = StatsRepository(self.db)

        ranking = await stats.get_teacher_ranking_paginated(
            academic_period_id=period_id,
            department_id=department_id,
            page=1,
            limit=1000,
            search=search,
            sort="asc",
        )

        teachers = ranking.get("teachers", [])
        teacher_ids = [t["teacher_id"] for t in teachers]

        averages_by_teacher = self._question_averages(teacher_ids, period_id)
        planned = self._teachers_with_plan(teacher_ids, period_id)

        result: list[dict] = []

        for teacher in teachers:
            teacher_id = teacher["teacher_id"]
            avg = teacher.get("overall_average")
            below_threshold = avg is not None and avg < threshold
            has_plan = teacher_id in planned

            if only_at_risk and (not below_threshold or has_plan):
                continue

            dimensions = self._build_indicators(
                averages_by_teacher.get(teacher_id, {}), threshold
            )

            weak_questions = [
                {**question, "dimension": dimension["dimension"]}
                for dimension in dimensions
                for question in dimension["questions"]
                if question["below_threshold"]
            ]

            result.append(
                {
                    "teacher_id": teacher_id,
                    "name": teacher.get("name"),
                    "avatar_url": teacher.get("avatar_url"),
                    "institutional_code": teacher.get("institutional_code"),
                    "overall_average": avg,
                    "below_threshold": below_threshold,
                    "has_plan": has_plan,
                    "dimensions": dimensions,
                    "weak_dimensions": [
                        d for d in dimensions if d["below_threshold"]
                    ],
                    "weak_questions": weak_questions,
                    "overall_suggestions": suggest_actions("OVERALL_AVERAGE"),
                }
            )

        return result

    async def get_at_risk(
        self,
        department_id: int,
        period_id: int,
        threshold: float,
    ) -> list[dict]:
        """Teachers below threshold in the period without a plan yet."""

        return await self.get_candidates(
            department_id=department_id,
            period_id=period_id,
            threshold=threshold,
            only_at_risk=True,
        )

    # ------------------------------------------------------------------ #
    # Teacher history (evaluaciones por periodo + planes + reincidencia)
    # ------------------------------------------------------------------ #
    def _period_question_averages(
        self, teacher_id: int
    ) -> dict[str, dict[str, float]]:
        """Per-period, per-question averages for one teacher, in one query.

        Keyed by period code so it can be merged with the overall history."""

        rows = (
            self.db.query(
                AcademicPeriodModel.code.label("period_code"),
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(
                AcademicPeriodModel,
                AcademicPeriodModel.id == EvaluationModel.academic_period_id,
            )
            .filter(AcademicGroupModel.teacher_id == teacher_id)
            .group_by(
                AcademicPeriodModel.code,
                EvaluationQuestionScoreModel.question_code,
            )
            .all()
        )

        averages: dict[str, dict[str, float]] = {}
        for row in rows:
            averages.setdefault(row.period_code, {})[row.question_code] = round(
                float(row.avg_score), 2
            )

        return averages

    @staticmethod
    def _indicator_label(target_type: str, target_ref: str | None) -> str:
        if target_type == "OVERALL_AVERAGE":
            return "Promedio general"
        if target_type == "QUESTION" and target_ref:
            return f"{target_ref} — {QUESTION_TEXT.get(target_ref, target_ref)}"
        return target_ref or target_type

    async def get_history(self, teacher_id: int) -> dict | None:
        """Full follow-up history of a teacher: overall + per-dimension average
        for every evaluated period, every improvement plan with its resolution,
        and the indicators the teacher relapsed on (same indicator targeted by
        plans of different origin periods)."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not teacher:
            return None

        stats = StatsRepository(self.db)
        overall_history = await stats.get_teacher_history(teacher_id) or []
        question_history = self._period_question_averages(teacher_id)

        periods = [
            {
                "period_code": entry["period_code"],
                "period_name": entry["period_name"],
                "overall_average": entry["overall_average"],
                "dimensions": {
                    dimension: self._dimension_average(
                        question_history.get(entry["period_code"], {}), codes
                    )
                    for dimension, codes in DIMENSION_MAP.items()
                },
            }
            for entry in overall_history
        ]

        plans = (
            self.db.query(ImprovementPlanModel)
            .filter(ImprovementPlanModel.teacher_id == teacher_id)
            .order_by(ImprovementPlanModel.created_at.asc())
            .all()
        )

        groups: dict[tuple[str, str | None], dict] = {}
        for plan in plans:
            origin_code = self._period_code(plan.origin_period_id)
            for item in plan.items:
                if item.target_type == "QUALITATIVE":
                    continue
                group = groups.setdefault(
                    (item.target_type, item.target_ref),
                    {"plan_ids": [], "origin_period_ids": set(), "period_codes": []},
                )
                if plan.id not in group["plan_ids"]:
                    group["plan_ids"].append(plan.id)
                    group["origin_period_ids"].add(plan.origin_period_id)
                    if origin_code:
                        group["period_codes"].append(origin_code)

        recurrences = [
            {
                "target_type": target_type,
                "target_ref": target_ref,
                "label": self._indicator_label(target_type, target_ref),
                "plan_ids": group["plan_ids"],
                "period_codes": group["period_codes"],
            }
            for (target_type, target_ref), group in groups.items()
            if len(group["origin_period_ids"]) >= 2
        ]

        name, avatar = self._teacher_info(teacher_id)

        return {
            "teacher_id": teacher_id,
            "teacher_name": name,
            "teacher_avatar_url": avatar,
            "department_id": teacher.department_id,
            "periods": periods,
            "plans": [self._enrich(plan) for plan in plans],
            "recurrences": recurrences,
        }


def get_improvement_plans_repository(db: Annotated[Session, Depends(get_db)]):
    """Get improvement plans repository"""

    return ImprovementPlansRepository(db)
