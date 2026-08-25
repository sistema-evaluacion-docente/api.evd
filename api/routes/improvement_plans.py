"""Routes for improvement plan operations (Plan de Seguimiento Docente)."""

from fastapi import Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse

from api.config import config
from api.controllers.improvement_plans import (
    ImprovementPlansController,
    get_improvement_plans_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.utils.file_validation import validate_file_size
from api.utils.plan_files import save_plan_evidence
from api.schemas.improvement_plan import (
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanEvidenceCommentCreate,
    ImprovementPlanEvidenceCommentOut,
    ImprovementPlanEvidenceOut,
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceRequestOut,
    ImprovementPlanEvidenceRequestUpdate,
    ImprovementPlanEvidenceReview,
    ImprovementPlanOut,
    ImprovementPlanUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/improvement-plans", tags=["Improvement Plans"])

MANAGER_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]
ANY_ROLE = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO, RoleName.DOCENTE]


async def _read_pdf(file: UploadFile) -> bytes:
    """Validate that the upload is a non-empty PDF within the size limit."""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    validate_file_size(pdf_bytes, config.MAX_UPLOAD_SIZE_MB)

    return pdf_bytes


@router.get("/", response_model=list[ImprovementPlanOut])
async def get_all_plans(
    pagination: PaginationDep,
    department_id: int | None = Query(default=None),
    period_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """List improvement plans of a department with pagination and filters."""

    return await controller.get_all(
        current_user,
        pagination,
        department_id=department_id,
        period_id=period_id,
        status=status,
        search=search,
        teacher_id=teacher_id,
    )


@router.get("/at-risk")
async def get_at_risk_teachers(
    period_id: int = Query(...),
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Teachers an improvement plan is suggested for, without one yet."""

    return await controller.get_at_risk(current_user, period_id, department_id)


@router.get("/candidates")
async def get_plan_candidates(
    period_id: int = Query(...),
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Every evaluated teacher of the department with their weak indicators."""

    return await controller.get_candidates(current_user, period_id, department_id)


@router.get("/periods")
async def get_evaluated_periods(
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Academic periods with evaluations loaded, selectable as plan origin."""

    return await controller.get_evaluated_periods(current_user, department_id)


@router.get("/indicators")
async def get_plan_indicators(
    _=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Catalogue of indicators and the five aspects of the official forms.

    Open to a DOCENTE too: it carries no plan data, and their own plan view
    groups its compromisos by the aspects of the official form.
    """

    return await controller.get_indicators()


@router.get("/my", response_model=list[ImprovementPlanOut])
async def get_my_plans(
    current_user=Depends(require_roles([RoleName.DOCENTE])),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Plans belonging to the calling teacher."""

    return await controller.get_my_plans(current_user)


@router.get("/teacher/{teacher_id}/courses")
async def get_teacher_courses(
    teacher_id: int,
    period_id: int = Query(...),
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Asignaturas of a teacher in a period, to prefill the official forms."""

    return await controller.get_teacher_courses(teacher_id, period_id, current_user)


@router.get("/teacher/{teacher_id}/history")
async def get_teacher_history(
    teacher_id: int,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Cross-period history of a teacher, including plan recurrences."""

    return await controller.get_history(teacher_id, current_user)


@router.post("/", response_model=ImprovementPlanOut, status_code=201)
async def create_plan(
    payload: ImprovementPlanCreate,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Create an improvement plan for a teacher."""

    return await controller.create(payload, current_user)


@router.get("/{plan_id}", response_model=ImprovementPlanOut)
async def get_plan_by_id(
    plan_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Get an improvement plan by id. A DOCENTE can only see their own plan."""

    return await controller.get_by_id(plan_id, current_user)


@router.put("/{plan_id}", response_model=ImprovementPlanOut)
async def update_plan(
    plan_id: int,
    payload: ImprovementPlanUpdate,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Update an improvement plan, its items and its asignaturas."""

    return await controller.update(plan_id, payload, current_user)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Delete an improvement plan — only the director of its department.

    Not open to an ADMIN on purpose: the plan is an agreement between a director
    and a teacher, and undoing it belongs to whoever agreed it.
    """

    await controller.delete(plan_id, current_user)

    return Response(status_code=204)


@router.put("/{plan_id}/case-report", response_model=ImprovementPlanOut)
async def upsert_case_report(
    plan_id: int,
    payload: ImprovementPlanCaseReportUpsert,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Record the Formato 1 complaint that originated the plan."""

    return await controller.upsert_case_report(plan_id, payload, current_user)


@router.put("/{plan_id}/checkpoints/{checkpoint_id}", response_model=ImprovementPlanOut)
async def update_checkpoint(
    plan_id: int,
    checkpoint_id: int,
    payload: ImprovementPlanCheckpointUpdate,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Fill in one of the two formal seguimientos, aspect by aspect."""

    return await controller.update_checkpoint(
        plan_id, checkpoint_id, payload, current_user
    )


@router.post("/{plan_id}/acta/close", response_model=ImprovementPlanOut)
async def close_acta(
    plan_id: int,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Freeze the acta content so it can be printed and signed."""

    return await controller.close_acta(plan_id, current_user)


@router.post("/{plan_id}/acta/reopen", response_model=ImprovementPlanOut)
async def reopen_acta(
    plan_id: int,
    current_user=Depends(require_roles([RoleName.ADMIN])),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Reopen a closed acta to correct it (ADMIN only)."""

    return await controller.reopen_acta(plan_id, current_user)


@router.post("/{plan_id}/close", response_model=ImprovementPlanOut)
async def close_plan(
    plan_id: int,
    payload: ImprovementPlanClose,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Close an improvement plan with the confirmed result."""

    return await controller.close(plan_id, payload, current_user)


@router.post(
    "/{plan_id}/documents/{format_type}/generate", response_model=ImprovementPlanOut
)
async def generate_document(
    plan_id: int,
    format_type: str,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Render an official form (formato-1|formato-2|formato-3) from the plan data."""

    return await controller.generate_document(plan_id, format_type, current_user)


@router.post(
    "/{plan_id}/documents/{format_type}/signed", response_model=ImprovementPlanOut
)
async def upload_signed_document(
    plan_id: int,
    format_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Upload the physically signed copy of an official form.

    For the acta (formato-2) this requires the acta to be closed and moves it to
    FIRMADA.
    """

    pdf_bytes = await _read_pdf(file)

    return await controller.upload_signed_document(
        plan_id, format_type, pdf_bytes, current_user, filename=file.filename
    )


@router.delete(
    "/{plan_id}/documents/{format_type}/signed", response_model=ImprovementPlanOut
)
async def delete_signed_document(
    plan_id: int,
    format_type: str,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Detach the signed copy of an official form — a wrong or outdated scan.

    The generated PDF stays in place, so the form simply goes back to asking for
    a signature. For the acta (formato-2) this walks FIRMADA back to CERRADA.
    """

    return await controller.delete_signed_document(plan_id, format_type, current_user)


@router.get(
    "/{plan_id}/evidence-requests",
    response_model=list[ImprovementPlanEvidenceRequestOut],
)
async def list_evidence_requests(
    plan_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Deliverables the director asked for on this plan."""

    return await controller.list_evidence_requests(plan_id, current_user)


@router.post(
    "/{plan_id}/evidence-requests",
    response_model=ImprovementPlanEvidenceRequestOut,
    status_code=201,
)
async def create_evidence_request(
    plan_id: int,
    payload: ImprovementPlanEvidenceRequestCreate,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Ask the teacher for a specific deliverable."""

    return await controller.create_evidence_request(plan_id, payload, current_user)


@router.get(
    "/{plan_id}/evidence-requests/{request_id}",
    response_model=ImprovementPlanEvidenceRequestOut,
)
async def get_evidence_request(
    plan_id: int,
    request_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """One request with its submissions and message thread."""

    return await controller.get_evidence_request(plan_id, request_id, current_user)


@router.put(
    "/{plan_id}/evidence-requests/{request_id}",
    response_model=ImprovementPlanEvidenceRequestOut,
)
async def update_evidence_request(
    plan_id: int,
    request_id: int,
    payload: ImprovementPlanEvidenceRequestUpdate,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Edit a requested deliverable."""

    return await controller.update_evidence_request(
        plan_id, request_id, payload, current_user
    )


@router.post(
    "/{plan_id}/evidence-requests/{request_id}/comments",
    response_model=ImprovementPlanEvidenceCommentOut,
    status_code=201,
)
async def add_evidence_comment(
    plan_id: int,
    request_id: int,
    payload: ImprovementPlanEvidenceCommentCreate,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Post a message on the request thread — director or teacher."""

    return await controller.add_evidence_comment(
        plan_id, request_id, payload, current_user
    )


@router.post(
    "/{plan_id}/evidences", response_model=ImprovementPlanEvidenceOut, status_code=201
)
async def upload_evidence(
    plan_id: int,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    item_id: int | None = Form(default=None),
    request_id: int | None = Form(default=None),
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Submit an evidence PDF, optionally answering a specific request."""

    pdf_bytes = await _read_pdf(file)
    file_url = save_plan_evidence(plan_id, pdf_bytes)

    return await controller.add_evidence(
        plan_id,
        file_url,
        current_user,
        description=description,
        item_id=item_id,
        request_id=request_id,
    )


@router.put(
    "/{plan_id}/evidences/{evidence_id}/review",
    response_model=ImprovementPlanEvidenceOut,
)
async def review_evidence(
    plan_id: int,
    evidence_id: int,
    payload: ImprovementPlanEvidenceReview,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Approve a submitted evidence or send it back for a new attempt."""

    return await controller.review_evidence(
        plan_id, evidence_id, payload, current_user
    )


@router.delete("/{plan_id}/evidences/{evidence_id}", status_code=204)
async def delete_evidence(
    plan_id: int,
    evidence_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Delete a submitted evidence — its uploader or a manager of the plan."""

    await controller.delete_evidence(plan_id, evidence_id, current_user)


@router.get(
    "/{plan_id}/evidences/{evidence_id}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def download_evidence(
    plan_id: int,
    evidence_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Download a submitted evidence file."""

    filepath, filename = await controller.get_evidence_file(
        plan_id, evidence_id, current_user
    )

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
    )


@router.get(
    "/{plan_id}/documents/{format_type}/word",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def download_document_word(
    plan_id: int,
    format_type: str,
    current_user=Depends(require_roles(MANAGER_ROLES)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Download an official form as an editable Word document.

    The acta is signed by hand and often needs a last-minute correction, so the
    director gets a working copy. It is rendered from the plan as it stands and
    is not tracked — the PDF remains the document of record.
    """

    content, filename = await controller.render_document_word(
        plan_id, format_type, current_user
    )

    return Response(
        content=content,
        media_type="application/msword",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{plan_id}/documents/{format_type}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def download_document(
    plan_id: int,
    format_type: str,
    generated: bool = Query(
        default=False, description="Force the unsigned generated copy"
    ),
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(get_improvement_plans_controller),
):
    """Download an official form — the signed copy when there is one."""

    filepath, filename = await controller.get_document_file(
        plan_id, format_type, current_user, prefer_generated=generated
    )

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
    )
