"""
Improvement plans controller (Plan de Seguimiento Docente)
"""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.improvement_plans import (
    get_improvement_plan_document_service,
    get_improvement_plan_evidence_service,
    get_improvement_plan_service,
)
from api.schemas.improvement_plan import (
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanEvidenceCommentCreate,
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceRequestUpdate,
    ImprovementPlanEvidenceReview,
    ImprovementPlanUpdate,
)
from api.services.improvement_plan_document_service import (
    ImprovementPlanDocumentService,
)
from api.services.improvement_plan_evidence_service import (
    ImprovementPlanEvidenceService,
)
from api.services.improvement_plan_service import ImprovementPlanService
from api.utils.dimensions import ASPECTS
from api.utils.improvement_suggestions import build_indicator_catalog


class ImprovementPlansController:
    """Improvement plans controller"""

    def __init__(
        self,
        service: ImprovementPlanService,
        document_service: ImprovementPlanDocumentService,
        evidence_service: ImprovementPlanEvidenceService,
    ):
        self.service = service
        self.document_service = document_service
        self.evidence_service = evidence_service

    async def get_all(
        self,
        current_user,
        pagination: PaginationParams,
        department_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        teacher_id: int | None = None,
    ):
        """List improvement plans with pagination and filters."""

        return await self.service.get_all(
            current_user,
            pagination,
            department_id=department_id,
            period_id=period_id,
            status=status,
            search=search,
            teacher_id=teacher_id,
        )

    async def get_by_id(self, plan_id: int, current_user):
        """Get an improvement plan by id."""

        return await self.service.get_by_id(plan_id, current_user)

    async def get_my_plans(
        self,
        current_user,
        pagination: PaginationParams,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
    ):
        """Plans belonging to the calling teacher."""

        return await self.service.get_my_plans(
            current_user,
            pagination,
            period_id=period_id,
            status=status,
            search=search,
        )

    async def get_candidates(
        self, current_user, period_id: int, department_id: int | None = None
    ):
        """Teachers of the department with their per-indicator averages."""

        return await self.service.get_candidates(current_user, period_id, department_id)

    async def get_at_risk(
        self, current_user, period_id: int, department_id: int | None = None
    ):
        """Teachers below the institutional threshold without a plan yet."""

        return await self.service.get_at_risk(current_user, period_id, department_id)

    async def get_evaluated_periods(self, current_user, department_id: int | None = None):
        """Academic periods with evaluations loaded."""

        return await self.service.get_evaluated_periods(current_user, department_id)

    async def get_indicators(self):
        """Catalogue of selectable indicators and official form aspects."""

        return {
            "threshold": self.service.get_threshold(),
            "aspects": ASPECTS,
            **build_indicator_catalog(),
        }

    async def get_history(self, teacher_id: int, current_user):
        """Cross-period history and plan recurrences of a teacher."""

        return await self.service.get_history(teacher_id, current_user)

    async def create(self, data: ImprovementPlanCreate, current_user):
        """Create an improvement plan."""

        return await self.service.create(data, current_user)

    async def update(self, plan_id: int, data: ImprovementPlanUpdate, current_user):
        """Update an improvement plan."""

        return await self.service.update(plan_id, data, current_user)

    async def delete(self, plan_id: int, current_user):
        """Delete an improvement plan and everything hanging off it."""

        return await self.service.delete(plan_id, current_user)

    async def upsert_case_report(
        self, plan_id: int, data: ImprovementPlanCaseReportUpsert, current_user
    ):
        """Create or update the Formato 1 case report of a plan."""

        return await self.service.upsert_case_report(plan_id, data, current_user)

    async def update_checkpoint(
        self,
        plan_id: int,
        checkpoint_id: int,
        data: ImprovementPlanCheckpointUpdate,
        current_user,
    ):
        """Record one of the two formal seguimientos.

        Formato 3 *is* that matrix, so it is re-rendered right here and the plan
        comes back already reflecting it: the director never has to remember to
        regenerate the form he just changed.
        """

        await self.service.update_checkpoint(
            plan_id, checkpoint_id, data, current_user
        )

        await self.document_service.refresh_followup_format(plan_id, current_user)

        return await self.service.get_by_id(plan_id, current_user)

    async def close_acta(self, plan_id: int, current_user):
        """Freeze the acta content ahead of signing."""

        return await self.service.close_acta(plan_id, current_user)

    async def reopen_acta(self, plan_id: int, current_user):
        """Reopen a closed acta (ADMIN only)."""

        return await self.service.reopen_acta(plan_id, current_user)

    async def close(self, plan_id: int, data: ImprovementPlanClose, current_user):
        """Close an improvement plan with the confirmed result."""

        return await self.service.close(plan_id, data, current_user)

    async def get_teacher_courses(self, teacher_id: int, period_id: int, current_user):
        """Asignaturas of a teacher in a period, to prefill the forms."""

        return await self.service.get_teacher_courses(
            teacher_id, period_id, current_user
        )

    async def generate_document(self, plan_id: int, format_type: str, current_user):
        """Render one of the three official forms filled with the plan data."""

        return await self.document_service.generate(plan_id, format_type, current_user)

    async def render_document_word(self, plan_id: int, format_type: str, current_user):
        """Editable Word copy of an official form."""

        return await self.document_service.render_word(
            plan_id, format_type, current_user
        )

    async def upload_signed_document(
        self,
        plan_id: int,
        format_type: str,
        pdf_bytes: bytes,
        current_user,
        filename: str | None = None,
    ):
        """Attach the physically signed copy of an official form."""

        return await self.document_service.upload_signed(
            plan_id, format_type, pdf_bytes, current_user, filename=filename
        )

    async def delete_signed_document(
        self, plan_id: int, format_type: str, current_user
    ):
        """Detach a signed copy that was attached by mistake."""

        return await self.document_service.delete_signed(
            plan_id, format_type, current_user
        )

    async def get_document_file(
        self,
        plan_id: int,
        format_type: str,
        current_user,
        prefer_generated: bool = False,
    ):
        """Path and filename of an official form, for download."""

        return await self.document_service.get_file(
            plan_id, format_type, current_user, prefer_generated=prefer_generated
        )


    async def list_evidence_requests(self, plan_id: int, current_user):
        """Deliverables requested on a plan."""

        return await self.evidence_service.list_requests(plan_id, current_user)

    async def get_evidence_request(self, plan_id: int, request_id: int, current_user):
        """One request with its submissions and thread."""

        return await self.evidence_service.get_request(plan_id, request_id, current_user)

    async def create_evidence_request(
        self, plan_id: int, data: ImprovementPlanEvidenceRequestCreate, current_user
    ):
        """Ask the teacher for a specific deliverable."""

        return await self.evidence_service.create_request(plan_id, data, current_user)

    async def update_evidence_request(
        self,
        plan_id: int,
        request_id: int,
        data: ImprovementPlanEvidenceRequestUpdate,
        current_user,
    ):
        """Edit a requested deliverable."""

        return await self.evidence_service.update_request(
            plan_id, request_id, data, current_user
        )

    async def add_evidence_comment(
        self,
        plan_id: int,
        request_id: int,
        data: ImprovementPlanEvidenceCommentCreate,
        current_user,
    ):
        """Post a message on a request thread."""

        return await self.evidence_service.add_comment(
            plan_id, request_id, data, current_user
        )

    async def add_evidence(
        self,
        plan_id: int,
        file_url: str,
        current_user,
        description: str | None = None,
        item_id: int | None = None,
        request_id: int | None = None,
    ):
        """Attach a submitted evidence file."""

        return await self.evidence_service.add_evidence(
            plan_id,
            file_url,
            current_user,
            description=description,
            item_id=item_id,
            request_id=request_id,
        )

    async def review_evidence(
        self,
        plan_id: int,
        evidence_id: int,
        data: ImprovementPlanEvidenceReview,
        current_user,
    ):
        """Approve a submitted evidence or send it back."""

        return await self.evidence_service.review_evidence(
            plan_id, evidence_id, data, current_user
        )

    async def delete_evidence(self, plan_id: int, evidence_id: int, current_user):
        """Remove a submitted evidence."""

        return await self.evidence_service.delete_evidence(
            plan_id, evidence_id, current_user
        )

    async def get_evidence_file(self, plan_id: int, evidence_id: int, current_user):
        """Path and filename of an evidence, for download."""

        return await self.evidence_service.get_evidence_file(
            plan_id, evidence_id, current_user
        )


def get_improvement_plans_controller(
    service: ImprovementPlanService = Depends(get_improvement_plan_service),
    document_service: ImprovementPlanDocumentService = Depends(
        get_improvement_plan_document_service
    ),
    evidence_service: ImprovementPlanEvidenceService = Depends(
        get_improvement_plan_evidence_service
    ),
):
    """Get improvement plans controller"""

    return ImprovementPlansController(service, document_service, evidence_service)
