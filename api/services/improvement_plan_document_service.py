"""
Improvement plan document service — renders the three official UFPS forms and
tracks their generated / physically-signed copies.
"""

import asyncio
import logging

from api.exceptions import ResourceNotFoundError, ValidationError
from api.repositories.improvement_plan_documents import (
    ImprovementPlanDocumentsRepository,
)
from api.repositories.improvement_plans import ImprovementPlansRepository
from api.schemas.notification import NotificationCreate, NotificationType
from api.services.audit_service import AuditService
from api.services.improvement_plan_service import ImprovementPlanService
from api.services.notification_service import NotificationService
from api.utils.dimensions import ASPECTS, STUDENT_COMMENTS_ASPECT
from api.utils.email_sender import send_email
from api.utils.plan_email import render_document_signed
from api.utils.plan_links import teacher_plan_path
from api.utils.improvement_plan_pdf import (
    FORMAT_TEMPLATES,
    render_formato,
    render_formato_word,
)
from api.utils.plan_files import delete_plan_file, save_plan_document

logger = logging.getLogger(__name__)

ENTITY = "improvement_plan_documents"

# URL-friendly slug -> stored format_type.
FORMAT_SLUGS = {
    "formato-1": "FORMATO_1",
    "formato-2": "FORMATO_2",
    "formato-3": "FORMATO_3",
}

ACTA_FORMAT = "FORMATO_2"

# How each form is named to the teacher: the number it is called by, and what
# it is. Kept apart because they read in different places — "Formato 2 firmado"
# as a heading, "el Formato 2 (Ficha de acuerdo)" inside a sentence.
#
# Formato 1 is missing on purpose: the case the academic programme reported is
# internal to the department, and the teacher is not told about it.
SIGNED_FORMAT_NAMES = {
    "FORMATO_2": ("Formato 2", "Ficha de acuerdo"),
    "FORMATO_3": ("Formato 3", "Plan de seguimiento"),
}

# The follow-up matrix printed by Formato 3 is the seguimientos section itself,
# so the form is re-rendered every time one of them is recorded.
FOLLOWUP_FORMAT = "FORMATO_3"


def resolve_format_type(slug: str) -> str:
    """Translate the public slug into the stored format identifier.

    Every one of the three is a valid slot to file a signed PDF into — the
    Formato 1 included, which is only ever filed and never rendered.
    """

    format_type = FORMAT_SLUGS.get(slug.lower())

    if not format_type:
        raise ValidationError(
            f"Formato inválido: '{slug}'. Use formato-1, formato-2 o formato-3"
        )

    return format_type


def resolve_renderable_format_type(slug: str) -> str:
    """Same, for the operations that draw the form themselves.

    The Formato 1 is the case an academic programme reported: it is written and
    signed outside the platform and arrives to the director by email, so there
    is nothing to render — asking for it is a mistake worth naming.
    """

    format_type = resolve_format_type(slug)

    if format_type not in FORMAT_TEMPLATES:
        raise ValidationError(
            f"El {format_type.replace('_', ' ').lower()} no lo genera la "
            "plataforma: es el caso que remite el programa académico y se "
            "adjunta ya diligenciado. Use formato-2 o formato-3"
        )

    return format_type


class ImprovementPlanDocumentService:
    """Service class for the official form documents of a plan."""

    def __init__(
        self,
        documents_repository: ImprovementPlanDocumentsRepository,
        improvement_plans_repository: ImprovementPlansRepository,
        plan_service: ImprovementPlanService,
        audit_service: AuditService,
        notification_service: NotificationService,
    ):
        self.documents_repository = documents_repository
        self.improvement_plans_repository = improvement_plans_repository
        self.plan_service = plan_service
        self.audit_service = audit_service
        self.notification_service = notification_service

    # ------------------------------------------------------------------ #
    # Rendering context
    # ------------------------------------------------------------------ #
    def build_context(self, plan: dict) -> dict:
        """Shape a plan dict into what the form templates expect.

        The heart of it is grouping the plan items under the five aspects of the
        official forms and cross-referencing each aspect with the two follow-up
        columns of Formato 3.
        """

        checkpoints = {c["stage"]: c for c in plan.get("checkpoints", [])}
        first = checkpoints.get("PRIMER_SEGUIMIENTO")
        second = checkpoints.get("SEGUNDO_SEGUIMIENTO")

        def note_for(checkpoint: dict | None, aspect: int) -> str | None:
            if not checkpoint:
                return None
            return next(
                (
                    n.get("note")
                    for n in checkpoint.get("aspect_notes", [])
                    if n.get("aspect") == aspect
                ),
                None,
            )

        aspects = []
        for entry in ASPECTS:
            number = entry["aspect"]
            aspects.append(
                {
                    "aspect": number,
                    "label": entry["label"],
                    # Deliberately not called "items": in Jinja a dict's `.items`
                    # resolves to the dict method, not the key.
                    "entries": [
                        item
                        for item in plan.get("items", [])
                        if item.get("aspect") == number
                    ],
                    "first_note": note_for(first, number),
                    "second_note": note_for(second, number),
                }
            )

        teacher = self.improvement_plans_repository.get_teacher_context(
            plan["teacher_id"]
        )

        return {
            "plan": plan,
            "aspects": aspects,
            "student_comments_aspect": STUDENT_COMMENTS_ASPECT,
            "courses": plan.get("courses", []),
            "case_report": plan.get("case_report"),
            "first_checkpoint": first,
            "second_checkpoint": second,
            "teacher_name": plan.get("teacher_name"),
            "teacher_code": teacher.get("code"),
            # The plan freezes the header the director agreed on; the teacher's
            # own faculty/department is only the fallback for older plans.
            "department_name": plan.get("department_name")
            or teacher.get("department_name"),
            "faculty_name": plan.get("faculty_name") or teacher.get("faculty_name"),
            "program_name": plan.get("program_name"),
        }

    # ------------------------------------------------------------------ #
    # Operations
    # ------------------------------------------------------------------ #
    def _render_and_store(self, plan: dict, format_type: str, actor_id: int | None) -> str:
        """Render one form from the plan as it stands and file it as the copy of
        record, dropping the PDF it replaces. Returns the new path."""

        pdf_bytes = render_formato(format_type, self.build_context(plan))
        filepath = save_plan_document(plan["id"], pdf_bytes, format_type.lower())

        _, previous = self.documents_repository.set_generated(
            plan["id"], format_type, filepath, actor_id
        )
        delete_plan_file(previous)

        return filepath

    async def generate(self, plan_id: int, slug: str, current_user) -> dict:
        """Render an official form filled with the plan data."""

        format_type = resolve_renderable_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        self._render_and_store(plan, format_type, (current_user or {}).get("id"))

        await self.audit_service.log(
            action="CREATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=f"Generó el {format_type.replace('_', ' ').lower()} del plan",
        )

        return await self.plan_service.get_by_id(plan_id, current_user)

    async def render_word(
        self, plan_id: int, slug: str, current_user
    ) -> tuple[bytes, str]:
        """Editable Word copy of an official form, rendered on the fly.

        Deliberately not stored nor tracked: the PDF is the document of record,
        this is the working copy the director corrects before printing it for
        signature. It is always rendered from the plan as it stands right now.
        """

        format_type = resolve_renderable_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        content = render_formato_word(format_type, self.build_context(plan))

        return content, f"{slug}_plan_{plan_id}.doc"

    async def upload_signed(
        self,
        plan_id: int,
        slug: str,
        pdf_bytes: bytes,
        current_user,
        filename: str | None = None,
    ) -> dict:
        """Attach the scanned copy carrying the handwritten signatures.

        For the acta (Formato 2) this is what completes the agreement: the
        signature — not a separate "close" step — is what freezes its content
        and puts the plan into force, so it is accepted straight from BORRADOR
        as long as the acta is actually filled in.
        """

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        if format_type == ACTA_FORMAT:
            self.plan_service.ensure_acta_complete(plan)

        filepath = save_plan_document(plan_id, pdf_bytes, f"{format_type.lower()}_firmado")

        _, previous = self.documents_repository.set_signed(
            plan_id,
            format_type,
            filepath,
            (current_user or {}).get("id"),
            filename=filename,
        )
        delete_plan_file(previous)

        if format_type == ACTA_FORMAT and plan.get("acta_status") != "FIRMADA":
            await self.improvement_plans_repository.set_acta_status(
                plan_id, "FIRMADA", closed_by=(current_user or {}).get("id")
            )

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=(
                f"Subió el {format_type.replace('_', ' ').lower()} firmado del plan"
            ),
        )

        await self._announce_signed(plan, format_type, current_user)

        return await self.plan_service.get_by_id(plan_id, current_user)

    async def _announce_signed(self, plan: dict, format_type: str, current_user) -> None:
        """Tell the teacher there is a signed copy of their plan to read.

        Without this the document simply turns up on the page one day: the
        teacher has no reason to go looking, and the signed form is what the
        agreement actually *is*. Best-effort, like every other notice in the
        module — the scan is already stored and audited by the time this runs.
        """

        naming = SIGNED_FORMAT_NAMES.get(format_type)

        if not naming:
            return

        format_name, format_label = naming

        try:
            contact = self.improvement_plans_repository.get_teacher_contact(
                plan["teacher_id"]
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("No se pudo resolver el contacto del docente")
            return

        if not contact:
            return

        actor_id = (current_user or {}).get("id")

        if contact.get("user_id") == actor_id:
            return

        try:
            await self.notification_service.create(
                NotificationCreate(
                    user_id=contact["user_id"],
                    title=f"{format_name} firmado",
                    message=(
                        f"Ya puedes ver y descargar el {format_name} "
                        f"({format_label}) firmado de tu plan «{plan['title']}»."
                    ),
                    type=NotificationType.SUCCESS,
                    link=teacher_plan_path(plan["id"]),
                ),
                actor_id=actor_id,
            )
        except Exception:
            logger.exception(
                "No se pudo notificar el formato firmado del plan %s", plan["id"]
            )

        if not contact.get("email"):
            return

        try:
            department = self.improvement_plans_repository.get_department_context(
                plan.get("department_id")
            ) if plan.get("department_id") else {}

            message = render_document_signed(
                plan_id=plan["id"],
                plan_title=plan["title"],
                format_name=format_name,
                format_label=format_label,
                teacher_name=contact["name"],
                teacher_email=contact["email"],
                director_name=(current_user or {}).get("name") or "",
                department_name=department.get("department_name"),
            )

            # smtplib blocks, and this runs on the event loop.
            await asyncio.to_thread(send_email, message)
        except Exception:
            logger.exception(
                "No se pudo enviar el correo del formato firmado del plan %s",
                plan["id"],
            )

    async def delete_signed(self, plan_id: int, slug: str, current_user) -> dict:
        """Detach the signed copy of a form — the escape hatch for a wrong scan.

        The generated PDF stays where it was, so the slot simply goes back to
        asking for a signed copy. For the acta this walks it all the way back to
        BORRADOR: undoing the signature is what makes the agreement editable
        again, so it is reserved to the director who owns the plan — an ADMIN
        must not be able to reopen an agreement signed by someone else.
        """

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)

        if format_type == ACTA_FORMAT:
            self.plan_service.ensure_is_department_director(current_user, plan)
        else:
            self.plan_service.ensure_can_manage(current_user, plan)

        previous = self.documents_repository.clear_signed(plan_id, format_type)

        if not previous:
            raise ResourceNotFoundError("Documento firmado del plan", slug)

        delete_plan_file(previous)

        if format_type == ACTA_FORMAT and plan.get("acta_status") != "BORRADOR":
            await self.improvement_plans_repository.set_acta_status(plan_id, "BORRADOR")

        await self.audit_service.log(
            action="DELETE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=(
                f"Eliminó el {format_type.replace('_', ' ').lower()} firmado del plan"
            ),
        )

        return await self.plan_service.get_by_id(plan_id, current_user)

    async def refresh_followup_format(self, plan_id: int, current_user) -> None:
        """Re-render Formato 3 after a seguimiento was recorded.

        The follow-up matrix *is* Formato 3, so the form is kept in step with it
        instead of asking the director to remember to regenerate it. Any signed
        copy is dropped along the way: it carries signatures over a page that no
        longer matches what the plan says.

        The signature goes first on purpose. If the render then fails, the row
        is merely left without a generated copy — which the next download draws
        again — instead of keeping a signature over content that moved on.
        """

        plan = await self.plan_service.get_by_id(plan_id, current_user)

        previous = self.documents_repository.clear_signed(plan_id, FOLLOWUP_FORMAT)
        delete_plan_file(previous)

        self._render_and_store(plan, FOLLOWUP_FORMAT, (current_user or {}).get("id"))

    async def get_file(
        self, plan_id: int, slug: str, current_user, prefer_generated: bool = False
    ) -> tuple[str, str]:
        """Path and download name of a form, authorizing the caller.

        Serves the signed copy when there is one, unless the caller explicitly
        asked for the generated original. A form that was never rendered is
        rendered now: the interface has no "generar" step any more, downloading
        is what asks for the document.

        The Formato 1 is the exception, because there is nothing to fall back on:
        it is only ever the PDF the director attached, so asking for one that was
        never attached is a missing document, not a document still to draw.
        """

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)

        document = self.documents_repository.get_by_format(plan_id, format_type)

        if document is None:
            filepath = None
        elif prefer_generated:
            filepath = document.generated_pdf_url
        else:
            filepath = document.signed_pdf_url or document.generated_pdf_url

        if not filepath:
            if format_type not in FORMAT_TEMPLATES:
                raise ResourceNotFoundError("Documento del plan", slug)

            filepath = self._render_and_store(
                plan, format_type, (current_user or {}).get("id")
            )

        return filepath, f"{slug}_plan_{plan_id}.pdf"
