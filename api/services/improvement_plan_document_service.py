"""
Improvement plan document service — renders the three official UFPS forms and
tracks their generated / physically-signed copies.
"""

from api.exceptions import ResourceNotFoundError, ValidationError
from api.repositories.improvement_plan_documents import (
    ImprovementPlanDocumentsRepository,
)
from api.repositories.improvement_plans import ImprovementPlansRepository
from api.services.audit_service import AuditService
from api.services.improvement_plan_service import ImprovementPlanService
from api.utils.dimensions import ASPECTS, STUDENT_COMMENTS_ASPECT
from api.utils.improvement_plan_pdf import (
    FORMAT_TEMPLATES,
    render_formato,
    render_formato_word,
)
from api.utils.plan_files import delete_plan_file, save_plan_document

ENTITY = "improvement_plan_documents"

# URL-friendly slug -> stored format_type.
FORMAT_SLUGS = {
    "formato-1": "FORMATO_1",
    "formato-2": "FORMATO_2",
    "formato-3": "FORMATO_3",
}

ACTA_FORMAT = "FORMATO_2"


def resolve_format_type(slug: str) -> str:
    """Translate the public slug into the stored format identifier."""

    format_type = FORMAT_SLUGS.get(slug.lower())

    if not format_type or format_type not in FORMAT_TEMPLATES:
        raise ValidationError(
            f"Formato inválido: '{slug}'. Use formato-1, formato-2 o formato-3"
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
    ):
        self.documents_repository = documents_repository
        self.improvement_plans_repository = improvement_plans_repository
        self.plan_service = plan_service
        self.audit_service = audit_service

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
    async def generate(self, plan_id: int, slug: str, current_user) -> dict:
        """Render an official form filled with the plan data."""

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        pdf_bytes = render_formato(format_type, self.build_context(plan))
        filepath = save_plan_document(plan_id, pdf_bytes, format_type.lower())

        _, previous = self.documents_repository.set_generated(
            plan_id, format_type, filepath, (current_user or {}).get("id")
        )
        delete_plan_file(previous)

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

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        content = render_formato_word(format_type, self.build_context(plan))

        return content, f"{slug}_plan_{plan_id}.doc"

    async def upload_signed(
        self, plan_id: int, slug: str, pdf_bytes: bytes, current_user
    ) -> dict:
        """Attach the scanned copy carrying the handwritten signatures.

        For the acta (Formato 2) this is what completes the lifecycle: it may
        only be uploaded once the acta is CERRADA, and it moves it to FIRMADA.
        """

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)
        self.plan_service.ensure_can_manage(current_user, plan)

        if format_type == ACTA_FORMAT and plan.get("acta_status") == "BORRADOR":
            raise ValidationError(
                "Debe cerrar el acta antes de subir la versión firmada"
            )

        filepath = save_plan_document(plan_id, pdf_bytes, f"{format_type.lower()}_firmado")

        _, previous = self.documents_repository.set_signed(
            plan_id, format_type, filepath, (current_user or {}).get("id")
        )
        delete_plan_file(previous)

        if format_type == ACTA_FORMAT and plan.get("acta_status") == "CERRADA":
            await self.improvement_plans_repository.set_acta_status(plan_id, "FIRMADA")

        await self.audit_service.log(
            action="UPDATE",
            entity_name=ENTITY,
            entity_id=plan_id,
            actor_id=(current_user or {}).get("id"),
            description=(
                f"Subió el {format_type.replace('_', ' ').lower()} firmado del plan"
            ),
        )

        return await self.plan_service.get_by_id(plan_id, current_user)

    async def get_file(
        self, plan_id: int, slug: str, current_user, prefer_generated: bool = False
    ) -> tuple[str, str]:
        """Path and download name of a form, authorizing the caller.

        Serves the signed copy when there is one, unless the caller explicitly
        asked for the generated original.
        """

        format_type = resolve_format_type(slug)
        plan = await self.plan_service.get_by_id(plan_id, current_user)

        document = self.documents_repository.get_by_format(plan_id, format_type)

        if not document:
            raise ResourceNotFoundError("Documento del plan", slug)

        if prefer_generated:
            filepath = document.generated_pdf_url
        else:
            filepath = document.signed_pdf_url or document.generated_pdf_url

        if not filepath:
            raise ResourceNotFoundError("Documento del plan", slug)

        return filepath, f"{slug}_plan_{plan_id}.pdf"
