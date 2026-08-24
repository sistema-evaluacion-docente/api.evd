"""
Improvement plan service (Plan de Seguimiento Docente).

Holds the business rules of the module: who may see or touch a plan, when the
acta freezes, and the validations the official UFPS forms imply.
"""

import asyncio
import logging

from api.core.pagination import PaginationParams
from api.exceptions import (
    PermissionDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.repositories.improvement_plans import ImprovementPlansRepository
from api.repositories.settings import SettingsRepository
from api.schemas.improvement_plan import (
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanUpdate,
)
from api.schemas.notification import NotificationCreate, NotificationType
from api.schemas.user import RoleName
from api.services.audit_service import AuditService
from api.services.notification_service import NotificationService
from api.utils.email_sender import send_email
from api.utils.plan_email import (
    close_result_label,
    render_plan_closed,
    render_plan_created,
)
from api.utils.plan_files import delete_plan_files
from api.utils.plan_links import teacher_plan_path

logger = logging.getLogger(__name__)

ENTITY = "improvement_plans"

DEFAULT_SCORE_THRESHOLD = 3.5
SCORE_THRESHOLD_SETTING = "improvement_plan.score_threshold"

# Fields that belong to the acta and freeze once it is CERRADA.
ACTA_LOCKED_FIELDS = (
    "acta_number",
    "acta_date",
    "council_observations",
    "items",
    "courses",
)

LOCKED_ACTA_STATUSES = ("CERRADA", "FIRMADA")


class ImprovementPlanService:
    """Service class for improvement plan operations."""

    def __init__(
        self,
        improvement_plans_repository: ImprovementPlansRepository,
        settings_repository: SettingsRepository,
        audit_service: AuditService,
        notification_service: NotificationService,
    ):
        self.improvement_plans_repository = improvement_plans_repository
        self.settings_repository = settings_repository
        self.audit_service = audit_service
        self.notification_service = notification_service

    # ------------------------------------------------------------------ #
    # Access control
    # ------------------------------------------------------------------ #
    @staticmethod
    def _roles(current_user) -> set[str]:
        return set((current_user or {}).get("roles", []))

    @staticmethod
    def _is_admin(current_user) -> bool:
        return RoleName.ADMIN.value in set((current_user or {}).get("roles", []))

    def department_filter(
        self, current_user, department_id: int | None
    ) -> int | None:
        """Department scope for a listing.

        A director is always pinned to their own department. An ADMIN may target
        any department explicitly; without one they fall back to their own (an
        admin who also directs a department) and only span the whole institution
        when they have none.
        """

        own = (current_user or {}).get("department_id")

        if self._is_admin(current_user):
            return department_id if department_id is not None else own

        if own is None:
            raise ValidationError("El usuario no tiene un departamento asignado")

        return own

    def require_department_id(self, current_user, department_id: int | None) -> int:
        """Department for the per-department aggregations.

        Unlike a listing these cannot span the institution, so an ADMIN has to
        say which department they mean.
        """

        resolved = self.department_filter(current_user, department_id)

        if resolved is None:
            raise ValidationError(
                "Debe indicar el departamento (department_id) para esta consulta"
            )

        return resolved

    def ensure_can_access(self, current_user, plan: dict) -> None:
        """Authorize reading a plan.

        ADMIN sees everything, a director only their department, and a DOCENTE
        only their own plan.
        """

        if self._is_admin(current_user):
            return

        roles = self._roles(current_user)
        user_id = (current_user or {}).get("id")

        if RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles:
            if plan.get("department_id") == (current_user or {}).get("department_id"):
                return

        if RoleName.DOCENTE.value in roles:
            owner_id = self.improvement_plans_repository.get_teacher_user_id(
                plan["teacher_id"]
            )
            if owner_id is not None and owner_id == user_id:
                return

        raise PermissionDeniedError("No tiene permisos para acceder a este plan")

    def ensure_can_manage(self, current_user, plan: dict) -> None:
        """Authorize mutating a plan — managers only, never the teacher."""

        if self._is_admin(current_user):
            return

        roles = self._roles(current_user)

        if RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles and plan.get(
            "department_id"
        ) == (current_user or {}).get("department_id"):
            return

        raise PermissionDeniedError("No tiene permisos para modificar este plan")

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def get_threshold(self) -> float:
        """Institutional score below which an indicator counts as weak."""

        setting = self.settings_repository.get_by_key(SCORE_THRESHOLD_SETTING)

        if not setting or setting.value is None:
            return DEFAULT_SCORE_THRESHOLD

        try:
            return float(setting.value)
        except (TypeError, ValueError):
            return DEFAULT_SCORE_THRESHOLD

    async def get_all(
        self,
        current_user,
        pagination: PaginationParams,
        department_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        teacher_id: int | None = None,
    ) -> dict:
        """List plans of a department with pagination and filters."""

        resolved_department_id = self.department_filter(current_user, department_id)

        # The repository already returns the {items,total,page,limit,pages} shape
        # ResponseEnvelopeMiddleware turns into `data` + `pagination`.
        return await self.improvement_plans_repository.get_all(
            department_id=resolved_department_id,
            period_id=period_id,
            status=status,
            search=search,
            teacher_id=teacher_id,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def get_by_id(self, plan_id: int, current_user) -> dict:
        """Get a plan by id, authorizing the caller."""

        plan = await self.improvement_plans_repository.get_by_id(plan_id)

        if not plan:
            raise ResourceNotFoundError("Plan de mejoramiento", plan_id)

        self.ensure_can_access(current_user, plan)

        return plan

    async def get_my_plans(self, current_user) -> list[dict]:
        """Plans of the teacher linked to the calling user."""

        teacher = self.improvement_plans_repository.get_teacher_by_user_id(
            (current_user or {}).get("id")
        )

        if not teacher:
            return []

        return await self.improvement_plans_repository.get_by_teacher(teacher.id)

    async def get_candidates(
        self, current_user, period_id: int, department_id: int | None = None
    ) -> list[dict]:
        """Every teacher of the department with their weak indicators."""

        resolved_department_id = self.require_department_id(current_user, department_id)

        return await self.improvement_plans_repository.get_candidates(
            department_id=resolved_department_id,
            period_id=period_id,
            threshold=self.get_threshold(),
        )

    async def get_at_risk(
        self, current_user, period_id: int, department_id: int | None = None
    ) -> list[dict]:
        """Candidates narrowed to those below the institutional threshold."""

        resolved_department_id = self.require_department_id(current_user, department_id)

        return await self.improvement_plans_repository.get_at_risk(
            department_id=resolved_department_id,
            period_id=period_id,
            threshold=self.get_threshold(),
        )

    async def get_evaluated_periods(
        self, current_user, department_id: int | None = None
    ) -> list[dict]:
        """Periods with evaluations loaded, selectable as plan origin."""

        resolved_department_id = self.require_department_id(current_user, department_id)

        return await self.improvement_plans_repository.get_evaluated_periods(
            resolved_department_id
        )

    async def get_teacher_courses(
        self, teacher_id: int, period_id: int, current_user
    ) -> list[dict]:
        """Asignaturas of a teacher in a period, to prefill the official forms."""

        if not self._is_admin(current_user):
            teacher_department = (
                self.improvement_plans_repository.get_teacher_department_id(teacher_id)
            )
            if teacher_department != (current_user or {}).get("department_id"):
                raise PermissionDeniedError(
                    "No tiene permisos para consultar este docente"
                )

        return await self.improvement_plans_repository.get_teacher_courses(
            teacher_id, period_id
        )

    async def get_history(self, teacher_id: int, current_user) -> dict:
        """Cross-period history of a teacher, including plan recurrences."""

        history = await self.improvement_plans_repository.get_history(teacher_id)

        if not history:
            raise ResourceNotFoundError("Docente", teacher_id)

        if not self._is_admin(current_user):
            owner_department = history.get("department_id")
            if owner_department != (current_user or {}).get("department_id"):
                raise PermissionDeniedError(
                    "No tiene permisos para consultar este docente"
                )

        return history

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    async def create(self, data: ImprovementPlanCreate, current_user) -> dict:
        """Create a plan, rejecting a duplicate for the same teacher/period."""

        if await self.improvement_plans_repository.has_plan_for(
            data.teacher_id, data.origin_period_id
        ):
            raise ResourceAlreadyExistsError(
                "plan de mejoramiento",
                "docente y periodo de origen",
                f"{data.teacher_id}/{data.origin_period_id}",
            )

        plan = await self.improvement_plans_repository.create(
            data, created_by=(current_user or {}).get("id")
        )

        self.ensure_can_manage(current_user, plan)

        await self.audit_service.log(
            action="CREATE",
            entity_name=ENTITY,
            entity_id=plan["id"],
            actor_id=(current_user or {}).get("id"),
            description=f"Creó el plan de mejoramiento '{plan['title']}'",
        )

        await self._announce_new_plan(plan, current_user)

        return plan

    async def _announce_new_plan(self, plan: dict, current_user) -> None:
        """Tell the teacher a plan has been drawn up for them.

        Best-effort, like the notifications of the evidence loop: the plan is
        already created and audited by the time this runs, so a mail server that
        is down or a teacher without an account must not turn a successful
        creation into a 500. Everything here is logged and swallowed.
        """

        try:
            contact = self.improvement_plans_repository.get_teacher_contact(
                plan["teacher_id"]
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("No se pudo resolver el contacto del docente")
            return

        if not contact:
            logger.info(
                "El docente %s no tiene usuario; no se le avisa del plan %s",
                plan["teacher_id"],
                plan["id"],
            )
            return

        actor_id = (current_user or {}).get("id")

        await self._notify_teacher(plan, contact, actor_id)
        await self._email_teacher(plan, contact, current_user)

    async def _notify_teacher(self, plan: dict, contact: dict, actor_id) -> None:
        """In-app notification, so the bell says it too."""

        try:
            await self.notification_service.create(
                NotificationCreate(
                    user_id=contact["user_id"],
                    title="Nuevo plan de mejoramiento",
                    message=(
                        f"Se registró a tu nombre el plan «{plan['title']}». "
                        "Revisa los compromisos acordados."
                    ),
                    type=NotificationType.INFO,
                    link=teacher_plan_path(plan["id"]),
                ),
                actor_id=actor_id,
            )
        except Exception:
            logger.exception(
                "No se pudo notificar en la app el plan %s", plan["id"]
            )

    async def _email_teacher(self, plan: dict, contact: dict, current_user) -> None:
        """The institutional email, with the letterhead and a link to the plan."""

        if not contact.get("email"):
            logger.info("El docente %s no tiene correo", plan["teacher_id"])
            return

        try:
            department = self.improvement_plans_repository.get_department_context(
                plan.get("department_id")
            )

            message = render_plan_created(
                plan_id=plan["id"],
                plan_title=plan["title"],
                teacher_name=contact["name"],
                teacher_email=contact["email"],
                director_name=(current_user or {}).get("name") or "",
                department_name=department.get("department_name"),
                period_code=plan.get("origin_period_code"),
            )

            # smtplib blocks, and this runs on the event loop.
            await asyncio.to_thread(send_email, message)
        except Exception:
            logger.exception(
                "No se pudo enviar el correo del plan %s a %s",
                plan["id"],
                contact.get("email"),
            )

    async def _announce_closed_plan(self, plan: dict, data, current_user) -> None:
        """Tell the teacher their plan has been settled.

        The twin of ``_announce_new_plan``, and best-effort for the same reason:
        the plan is already closed and audited by the time this runs, so a mail
        server that is down must not turn a successful closing into a 500.
        """

        try:
            contact = self.improvement_plans_repository.get_teacher_contact(
                plan["teacher_id"]
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("No se pudo resolver el contacto del docente")
            return

        if not contact:
            logger.info(
                "El docente %s no tiene usuario; no se le avisa del cierre del plan %s",
                plan["teacher_id"],
                plan["id"],
            )
            return

        result = data.result.value
        reason = (data.reason or "").strip() or None

        await self._notify_teacher_of_closing(plan, contact, result, current_user)
        await self._email_teacher_of_closing(plan, contact, result, reason, current_user)

    async def _notify_teacher_of_closing(
        self, plan: dict, contact: dict, result: str, current_user
    ) -> None:
        """In-app notification, so the bell says it too."""

        try:
            await self.notification_service.create(
                NotificationCreate(
                    user_id=contact["user_id"],
                    title="Plan de mejoramiento cerrado",
                    message=(
                        f"Se cerró el plan «{plan['title']}» con resultado "
                        f"{close_result_label(result).lower()}."
                    ),
                    type=(
                        NotificationType.SUCCESS
                        if result == "CUMPLIDO"
                        else NotificationType.INFO
                    ),
                    link=teacher_plan_path(plan["id"]),
                ),
                actor_id=(current_user or {}).get("id"),
            )
        except Exception:
            logger.exception(
                "No se pudo notificar en la app el cierre del plan %s", plan["id"]
            )

    async def _email_teacher_of_closing(
        self, plan: dict, contact: dict, result: str, reason: str | None, current_user
    ) -> None:
        """The institutional email, with the letterhead and the verdict."""

        if not contact.get("email"):
            logger.info("El docente %s no tiene correo", plan["teacher_id"])
            return

        try:
            department = self.improvement_plans_repository.get_department_context(
                plan.get("department_id")
            )

            message = render_plan_closed(
                plan_id=plan["id"],
                plan_title=plan["title"],
                teacher_name=contact["name"],
                teacher_email=contact["email"],
                director_name=(current_user or {}).get("name") or "",
                department_name=department.get("department_name"),
                result=result,
                reason=reason,
                period_code=plan.get("origin_period_code"),
            )

            # smtplib blocks, and this runs on the event loop.
            await asyncio.to_thread(send_email, message)
        except Exception:
            logger.exception(
                "No se pudo enviar el correo de cierre del plan %s a %s",
                plan["id"],
                contact.get("email"),
            )

    async def delete(self, plan_id: int, current_user) -> bool:
        """Remove a plan for good — the director's own call.

        Deliberately not gated on the acta being signed: a plan drawn up for the
        wrong teacher has to be undoable, and the signature does not make the
        mistake right. What protects the signed ones is the confirmation the
        director is shown, which spells out what disappears.

        Not an ADMIN's call, though: like undoing a signature, this belongs to
        the director who agreed the plan with the teacher.
        """

        plan = await self.get_by_id(plan_id, current_user)

        self.ensure_is_department_director(current_user, plan)

        # Audited before the row is gone, so the description can still name it.
        await self.audit_service.log(
            action="DELETE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Eliminó el plan de mejoramiento '{plan['title']}'",
        )

        deleted = await self.improvement_plans_repository.delete(plan_id)

        if deleted:
            # After the row, so a failed delete does not strand the plan
            # pointing at PDFs that are no longer there.
            delete_plan_files(plan_id)

        return deleted

    def ensure_acta_complete(self, plan: dict) -> None:
        """Reject freezing an acta that is not filled in yet.

        Signing the Formato 2 is what turns the agreement into the copy of
        record, so the acto administrativo backing it and at least one agreed
        commitment must already be there — otherwise the department would file a
        signed blank.
        """

        if not plan.get("acta_number") or not plan.get("acta_date"):
            raise ValidationError(
                "Debe registrar el número y la fecha del acta antes de firmarla"
            )

        if not any(item.get("commitment") for item in plan.get("items", [])):
            raise ValidationError(
                "El acta debe tener al menos un compromiso registrado"
            )

    def ensure_is_department_director(self, current_user, plan: dict) -> None:
        """Authorize an action reserved to the director who owns the plan.

        Unlike :meth:`ensure_can_manage` an ADMIN is *not* waved through: undoing
        the signature of an agreement reopens it for editing, and that call
        belongs to the director who signed it with the teacher.
        """

        roles = self._roles(current_user)

        if RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles and plan.get(
            "department_id"
        ) == (current_user or {}).get("department_id"):
            return

        raise PermissionDeniedError(
            "Solo el director del departamento puede realizar esta acción"
        )

    def _ensure_acta_editable(self, plan: dict, payload: dict) -> None:
        """Reject edits to acta content once the acta is closed.

        Only the acta freezes — title, dates and follow-ups stay editable so the
        plan can keep being tracked after the agreement is signed.
        """

        if plan.get("acta_status") not in LOCKED_ACTA_STATUSES:
            return

        touched = [f for f in ACTA_LOCKED_FIELDS if payload.get(f) is not None]

        if touched:
            raise ValidationError(
                "El acta está cerrada; no se puede modificar su contenido "
                f"({', '.join(touched)})"
            )

    async def update(
        self, plan_id: int, data: ImprovementPlanUpdate, current_user
    ) -> dict:
        """Update a plan and, if provided, replace its items and courses."""

        plan = await self.get_by_id(plan_id, current_user)
        self.ensure_can_manage(current_user, plan)
        self._ensure_acta_editable(plan, data.model_dump(exclude_unset=True))

        updated = await self.improvement_plans_repository.update(plan_id, data)

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Actualizó el plan de mejoramiento '{updated['title']}'",
        )

        return updated

    async def upsert_case_report(
        self, plan_id: int, data: ImprovementPlanCaseReportUpsert, current_user
    ) -> dict:
        """Record the Formato 1 complaint that originated the plan."""

        plan = await self.get_by_id(plan_id, current_user)
        self.ensure_can_manage(current_user, plan)

        updated = await self.improvement_plans_repository.upsert_case_report(
            plan_id, data, reported_by=(current_user or {}).get("id")
        )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description="Actualizó el caso reportado (Formato 1) del plan",
        )

        return updated

    async def update_checkpoint(
        self,
        plan_id: int,
        checkpoint_id: int,
        data: ImprovementPlanCheckpointUpdate,
        current_user,
    ) -> dict:
        """Fill in one of the two formal seguimientos."""

        plan = await self.get_by_id(plan_id, current_user)
        self.ensure_can_manage(current_user, plan)

        updated = await self.improvement_plans_repository.update_checkpoint(
            plan_id, checkpoint_id, data
        )

        if not updated:
            raise ResourceNotFoundError("Seguimiento", checkpoint_id)

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description="Registró un seguimiento del plan de mejoramiento",
        )

        return updated

    async def close_acta(self, plan_id: int, current_user) -> dict:
        """Freeze the acta content so it can be printed and signed."""

        plan = await self.get_by_id(plan_id, current_user)
        self.ensure_can_manage(current_user, plan)

        if plan.get("acta_status") in LOCKED_ACTA_STATUSES:
            raise ValidationError("El acta ya está cerrada")

        self.ensure_acta_complete(plan)

        updated = await self.improvement_plans_repository.set_acta_status(
            plan_id, "CERRADA", closed_by=(current_user or {}).get("id")
        )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Cerró el acta {plan.get('acta_number')} del plan",
        )

        return updated

    async def reopen_acta(self, plan_id: int, current_user) -> dict:
        """Reopen a closed acta. ADMIN-only escape hatch for corrections."""

        if not self._is_admin(current_user):
            raise PermissionDeniedError("Solo un administrador puede reabrir un acta")

        plan = await self.get_by_id(plan_id, current_user)

        if plan.get("acta_status") == "BORRADOR":
            raise ValidationError("El acta ya está en borrador")

        updated = await self.improvement_plans_repository.set_acta_status(
            plan_id, "BORRADOR"
        )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description="Reabrió el acta del plan de mejoramiento",
        )

        return updated

    async def close(
        self, plan_id: int, data: ImprovementPlanClose, current_user
    ) -> dict:
        """Close the plan with the confirmed result."""

        plan = await self.get_by_id(plan_id, current_user)
        self.ensure_can_manage(current_user, plan)

        updated = await self.improvement_plans_repository.close(
            plan_id, data.result.value, data.reason
        )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Cerró el plan de mejoramiento como {data.result.value}",
        )

        await self._announce_closed_plan(updated or plan, data, current_user)

        return updated
