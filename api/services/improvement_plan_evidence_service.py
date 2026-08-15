"""
Improvement plan evidence service.

Runs the deliverable loop the director asked for: he requests a specific piece of
evidence, the teacher submits it, both sides can comment, and the director
approves it or sends it back for a new submission.
"""

from api.exceptions import ResourceNotFoundError, ValidationError
from api.repositories.improvement_plan_evidences import (
    ImprovementPlanEvidencesRepository,
)
from api.repositories.improvement_plans import ImprovementPlansRepository
from api.schemas.improvement_plan import (
    EvidenceStatus,
    ImprovementPlanEvidenceCommentCreate,
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceRequestUpdate,
    ImprovementPlanEvidenceReview,
)
from api.schemas.notification import NotificationCreate, NotificationType
from api.services.audit_service import AuditService
from api.services.improvement_plan_service import ImprovementPlanService
from api.services.notification_service import NotificationService
from api.utils.plan_files import delete_plan_file

ENTITY = "improvement_plan_evidences"
REQUEST_ENTITY = "improvement_plan_evidence_requests"

CLOSED_PLAN_STATUSES = (
    "CERRADO_CUMPLIDO",
    "CERRADO_NO_CUMPLIDO",
    "CERRADO_MANUAL",
)


def _plan_link(plan_id: int) -> str:
    """Deep link the notification should take the user to."""

    return f"/plans/{plan_id}"


class ImprovementPlanEvidenceService:
    """Service class for the evidence request/review workflow."""

    def __init__(
        self,
        evidences_repository: ImprovementPlanEvidencesRepository,
        improvement_plans_repository: ImprovementPlansRepository,
        plan_service: ImprovementPlanService,
        notification_service: NotificationService,
        audit_service: AuditService,
    ):
        self.evidences_repository = evidences_repository
        self.improvement_plans_repository = improvement_plans_repository
        self.plan_service = plan_service
        self.notification_service = notification_service
        self.audit_service = audit_service

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ensure_open(plan: dict) -> None:
        """Evidence can only move while the plan is still being followed up."""

        if plan.get("status") in CLOSED_PLAN_STATUSES:
            raise ValidationError(
                "El plan está cerrado; no se pueden gestionar evidencias"
            )

    def _teacher_user_id(self, plan: dict) -> int | None:
        return self.improvement_plans_repository.get_teacher_user_id(
            plan["teacher_id"]
        )

    def _is_plan_teacher(self, plan: dict, current_user) -> bool:
        owner_id = self._teacher_user_id(plan)

        return owner_id is not None and owner_id == (current_user or {}).get("id")

    async def _notify(
        self,
        user_id: int | None,
        title: str,
        message: str,
        plan_id: int,
        actor_id: int | None,
        notification_type: NotificationType = NotificationType.INFO,
    ) -> None:
        """Best-effort notification; never blocks the main operation."""

        if not user_id or user_id == actor_id:
            return

        await self.notification_service.create(
            NotificationCreate(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                link=_plan_link(plan_id),
            ),
            actor_id=actor_id,
        )

    async def _notify_director(
        self, plan: dict, title: str, message: str, actor_id: int | None
    ) -> None:
        director_user_id = self.improvement_plans_repository.get_department_director_user_id(
            plan.get("department_id")
        )

        await self._notify(director_user_id, title, message, plan["id"], actor_id)

    # ------------------------------------------------------------------ #
    # Requests
    # ------------------------------------------------------------------ #
    async def list_requests(self, plan_id: int, current_user) -> list[dict]:
        """Deliverables requested on a plan — visible to the teacher too."""

        await self.plan_service.get_by_id(plan_id, current_user)

        return await self.evidences_repository.list_requests(plan_id)

    async def get_request(self, plan_id: int, request_id: int, current_user) -> dict:
        """One request with its submissions and message thread."""

        await self.plan_service.get_by_id(plan_id, current_user)

        request = await self.evidences_repository.get_request_detail(
            plan_id, request_id
        )

        if not request:
            raise ResourceNotFoundError("Solicitud de evidencia", request_id)

        return request

    async def create_request(
        self, plan_id: int, data: ImprovementPlanEvidenceRequestCreate, current_user
    ) -> dict:
        """Ask the teacher for a specific deliverable."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)
        self._ensure_open(plan)

        request = await self.evidences_repository.create_request(
            plan_id, data, requested_by=(current_user or {}).get("id")
        )

        await self.audit_service.log(
            action="CREATE",
            entity_name=REQUEST_ENTITY,
            entity_id=request["id"],
            actor_id=(current_user or {}).get("id"),
            description=f"Solicitó la evidencia '{data.title}' en el plan {plan_id}",
        )

        await self._notify(
            self._teacher_user_id(plan),
            "Nueva evidencia solicitada",
            f"El director solicitó: {data.title}",
            plan_id,
            (current_user or {}).get("id"),
            NotificationType.WARNING,
        )

        return request

    async def update_request(
        self,
        plan_id: int,
        request_id: int,
        data: ImprovementPlanEvidenceRequestUpdate,
        current_user,
    ) -> dict:
        """Edit a requested deliverable."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        request = await self.evidences_repository.update_request(
            plan_id, request_id, data
        )

        if not request:
            raise ResourceNotFoundError("Solicitud de evidencia", request_id)

        await self.audit_service.log(
            action="UPDATE",
            entity_name=REQUEST_ENTITY,
            entity_id=request_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Actualizó la solicitud de evidencia {request_id}",
        )

        return request

    # ------------------------------------------------------------------ #
    # Thread
    # ------------------------------------------------------------------ #
    async def add_comment(
        self,
        plan_id: int,
        request_id: int,
        data: ImprovementPlanEvidenceCommentCreate,
        current_user,
    ) -> dict:
        """Post a message on a request thread — either side may write."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self._ensure_open(plan)

        if not self.evidences_repository.get_request(plan_id, request_id):
            raise ResourceNotFoundError("Solicitud de evidencia", request_id)

        comment = await self.evidences_repository.add_comment(
            request_id, data.body, author_id=(current_user or {}).get("id")
        )

        actor_id = (current_user or {}).get("id")

        if self._is_plan_teacher(plan, current_user):
            await self._notify_director(
                plan,
                "Comentario del docente",
                data.body[:120],
                actor_id,
            )
        else:
            await self._notify(
                self._teacher_user_id(plan),
                "Comentario del director",
                data.body[:120],
                plan_id,
                actor_id,
            )

        return comment

    # ------------------------------------------------------------------ #
    # Evidences
    # ------------------------------------------------------------------ #
    async def add_evidence(
        self,
        plan_id: int,
        file_url: str,
        current_user,
        description: str | None = None,
        item_id: int | None = None,
        request_id: int | None = None,
    ) -> dict:
        """Attach a submitted file, optionally answering a request."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self._ensure_open(plan)

        if item_id is not None and not any(
            i["id"] == item_id for i in plan.get("items", [])
        ):
            raise ValidationError("El ítem indicado no pertenece a este plan")

        if request_id is not None and not self.evidences_repository.get_request(
            plan_id, request_id
        ):
            raise ResourceNotFoundError("Solicitud de evidencia", request_id)

        evidence = await self.evidences_repository.add_evidence(
            plan_id,
            file_url,
            description=description,
            item_id=item_id,
            request_id=request_id,
            uploaded_by=(current_user or {}).get("id"),
        )

        actor_id = (current_user or {}).get("id")

        # A submission puts the request back in the director's court.
        if request_id is not None:
            self.evidences_repository.set_request_status(request_id, "EN_REVISION")

        await self.audit_service.log(
            action="CREATE",
            entity_name=ENTITY,
            entity_id=evidence["id"],
            actor_id=actor_id,
            description=f"Adjuntó una evidencia al plan {plan_id}",
        )

        if self._is_plan_teacher(plan, current_user):
            await self._notify_director(
                plan,
                "Nueva evidencia enviada",
                "El docente adjuntó una evidencia pendiente de revisión.",
                actor_id,
            )

        return evidence

    async def review_evidence(
        self,
        plan_id: int,
        evidence_id: int,
        data: ImprovementPlanEvidenceReview,
        current_user,
    ) -> dict:
        """Approve a submitted evidence or send it back for a new attempt."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)
        self._ensure_open(plan)

        evidence = self.evidences_repository.get_evidence(plan_id, evidence_id)

        if not evidence:
            raise ResourceNotFoundError("Evidencia", evidence_id)

        request_id = evidence.request_id
        actor_id = (current_user or {}).get("id")

        reviewed = await self.evidences_repository.review_evidence(
            evidence_id, data.status.value, actor_id
        )

        if data.comment and request_id:
            await self.evidences_repository.add_comment(
                request_id, data.comment, author_id=actor_id
            )

        if request_id:
            if data.status == EvidenceStatus.APROBADA:
                self.evidences_repository.set_request_status(request_id, "APROBADA")
            else:
                # Rejected: reopen so the teacher can submit again.
                self.evidences_repository.set_request_status(request_id, "PENDIENTE")
                await self.evidences_repository.add_comment(
                    request_id,
                    "La evidencia fue rechazada. Se requiere una nueva entrega.",
                    is_system=True,
                )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=evidence_id,
            actor_id=actor_id,
            description=f"Revisó la evidencia {evidence_id} como {data.status.value}",
        )

        approved = data.status == EvidenceStatus.APROBADA

        await self._notify(
            self._teacher_user_id(plan),
            "Evidencia aprobada" if approved else "Evidencia rechazada",
            data.comment
            or (
                "El director aprobó la evidencia."
                if approved
                else "El director rechazó la evidencia; debe enviar una nueva."
            ),
            plan_id,
            actor_id,
            NotificationType.SUCCESS if approved else NotificationType.WARNING,
        )

        return reviewed

    async def delete_evidence(
        self, plan_id: int, evidence_id: int, current_user
    ) -> None:
        """Remove an evidence — its uploader or a manager of the plan."""

        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self._ensure_open(plan)

        evidence = self.evidences_repository.get_evidence(plan_id, evidence_id)

        if not evidence:
            raise ResourceNotFoundError("Evidencia", evidence_id)

        actor_id = (current_user or {}).get("id")
        is_uploader = evidence.uploaded_by == actor_id

        if not is_uploader:
            self.plan_service.ensure_can_manage(current_user, plan)

        file_url = await self.evidences_repository.delete_evidence(
            plan_id, evidence_id
        )
        delete_plan_file(file_url)

        await self.audit_service.log(
            action="DELETE",
            entity_name=ENTITY,
            entity_id=evidence_id,
            actor_id=actor_id,
            description=f"Eliminó la evidencia {evidence_id} del plan {plan_id}",
        )

    async def get_evidence_file(
        self, plan_id: int, evidence_id: int, current_user
    ) -> tuple[str, str]:
        """Path and download name of an evidence, authorizing the caller."""

        await self.plan_service.get_by_id(plan_id, current_user)

        evidence = self.evidences_repository.get_evidence(plan_id, evidence_id)

        if not evidence or not evidence.file_url:
            raise ResourceNotFoundError("Evidencia", evidence_id)

        return evidence.file_url, f"evidencia_{evidence_id}.pdf"
