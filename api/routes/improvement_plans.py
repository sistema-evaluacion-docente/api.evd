"""
Routes for improvement plan operations (Plan de Seguimiento Docente).
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from api.config import config
from api.controllers.improvement_plans import (
    ImprovementPlansController,
    get_improvement_plans_controller,
)
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.improvement_plan import (
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanDetailResponse,
    ImprovementPlanListResponse,
    ImprovementPlanUpdate,
)
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName
from api.utils.file_validation import validate_file_size

router = APIRouter(prefix="/improvement-plans", tags=["Improvement Plans"])

DIRECTOR_OR_ADMIN = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]
ANY_ROLE = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO, RoleName.DOCENTE]


def _effective_department_id(
    current_user: dict, department_id: int | None
) -> int | None:
    """ADMIN may target any department via query; a director defaults to theirs."""

    if department_id is not None:
        return department_id
    return current_user.get("department_id")


def _is_closed(plan: dict) -> bool:
    return str(plan.get("status", "")).startswith("CERRADO")


async def _read_pdf(file: UploadFile) -> bytes:
    """Validate that the upload is a non-empty PDF within the size limit."""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    validate_file_size(pdf_bytes, config.MAX_UPLOAD_SIZE_MB)

    return pdf_bytes


def _save_plan_pdf(plan_id: int, pdf_bytes: bytes, prefix: str) -> str:
    """Persist a plan PDF under the uploads dir and return its relative path
    (served by the StaticFiles mount)."""

    plan_dir = os.path.join(config.UPLOAD_DIR, "improvement_plans", str(plan_id))
    os.makedirs(plan_dir, exist_ok=True)

    filepath = os.path.join(plan_dir, f"{prefix}_{uuid.uuid4().hex}.pdf")

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return filepath


def _delete_upload(filepath: str | None) -> None:
    """Best-effort removal of a replaced/deleted file, only inside UPLOAD_DIR."""

    if not filepath:
        return

    uploads_root = os.path.abspath(config.UPLOAD_DIR)
    target = os.path.abspath(filepath)

    if target.startswith(uploads_root + os.sep) and os.path.isfile(target):
        try:
            os.remove(target)
        except OSError:
            pass


def _ensure_can_access(
    controller: ImprovementPlansController, current_user: dict, plan: dict
) -> None:
    if not controller.can_access_plan(current_user, plan):
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para acceder a este plan",
        )


@router.get(
    "/",
    response_model=ImprovementPlanListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_plans(
    department_id: int | None = Query(default=None),
    period_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    teacher_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """List improvement plans with pagination and filters."""

    effective_department = _effective_department_id(current_user, department_id)

    result = await controller.get_all(
        department_id=effective_department,
        period_id=period_id,
        status=status,
        search=search,
        teacher_id=teacher_id,
        page=page,
        limit=limit,
    )

    return ResponseSchema(
        status=200,
        message="Improvement plans found",
        data=result["items"],
        pagination=Pagination(
            total=result["total"],
            page=result["page"],
            limit=result["limit"],
            pages=result["pages"],
        ),
        path="/improvement-plans",
    )


@router.get(
    "/at-risk",
    response_model=ResponseSchema,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def get_at_risk_teachers(
    period_id: int = Query(..., description="Academic period to inspect"),
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Teachers below the institutional threshold that have no plan yet for the
    period, with weak dimensions and suggested improvement actions."""

    effective_department = _effective_department_id(current_user, department_id)

    if effective_department is None:
        raise HTTPException(
            status_code=400,
            detail="Se requiere un department_id (el usuario no tiene departamento asignado)",
        )

    teachers = await controller.get_at_risk(period_id, effective_department)

    return ResponseSchema(
        status=200,
        message="At-risk teachers found",
        data=teachers,
        path="/improvement-plans/at-risk",
    )


@router.get(
    "/candidates",
    response_model=ResponseSchema,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def get_plan_candidates(
    period_id: int = Query(..., description="Academic period to inspect"),
    department_id: int | None = Query(default=None),
    only_at_risk: bool = Query(
        default=False,
        description="Only teachers below the threshold without a plan yet",
    ),
    search: str | None = Query(default=None, min_length=1),
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Teachers that can receive a plan, with the average of every dimension and
    of every question of the evaluation form.

    Returns the whole department by default: a teacher with a healthy overall
    average may still be below the threshold in a single question."""

    effective_department = _effective_department_id(current_user, department_id)

    if effective_department is None:
        raise HTTPException(
            status_code=400,
            detail="Se requiere un department_id (el usuario no tiene departamento asignado)",
        )

    result = await controller.get_candidates(
        period_id=period_id,
        department_id=effective_department,
        only_at_risk=only_at_risk,
        search=search,
    )

    return ResponseSchema(
        status=200,
        message="Plan candidates found",
        data=result,
        path="/improvement-plans/candidates",
    )


@router.get(
    "/periods",
    response_model=ResponseSchema,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def get_evaluated_periods(
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Periods the department already has grades for — the ones a plan can take
    as origin period. The current academic period usually has none yet."""

    effective_department = _effective_department_id(current_user, department_id)

    if effective_department is None:
        raise HTTPException(
            status_code=400,
            detail="Se requiere un department_id (el usuario no tiene departamento asignado)",
        )

    return ResponseSchema(
        status=200,
        message="Evaluated periods found",
        data=await controller.get_evaluated_periods(effective_department),
        path="/improvement-plans/periods",
    )


@router.get(
    "/indicators",
    response_model=ResponseSchema,
    responses={403: {"description": "Forbidden"}},
)
async def get_plan_indicators(
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Indicators a plan item can commit to: the overall average, each dimension
    as a whole, and each question of the evaluation form within it."""

    return ResponseSchema(
        status=200,
        message="Plan indicators found",
        data=await controller.get_indicators(),
        path="/improvement-plans/indicators",
    )


@router.get(
    "/my",
    response_model=ImprovementPlanListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_my_plans(
    current_user=Depends(require_roles([RoleName.DOCENTE])),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Plans of the authenticated teacher (vista del docente)."""

    plans = await controller.get_my_plans(current_user)

    return ResponseSchema(
        status=200,
        message="Improvement plans found",
        data=plans,
        pagination=Pagination(
            total=len(plans), page=1, limit=max(len(plans), 1), pages=1
        ),
        path="/improvement-plans/my",
    )


@router.get(
    "/teacher/{teacher_id}/history",
    response_model=ResponseSchema,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def get_teacher_history(
    teacher_id: int,
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Cross-period history of a teacher: overall and per-dimension averages
    for every evaluated period, every improvement plan with its resolution,
    and recurrence flags (same indicator planned in different periods)."""

    history = await controller.get_history(teacher_id)

    if not history:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            path=f"/improvement-plans/teacher/{teacher_id}/history",
        )

    roles = set(current_user.get("roles", []))
    if RoleName.ADMIN.value not in roles and history.get(
        "department_id"
    ) != current_user.get("department_id"):
        raise HTTPException(
            status_code=403,
            detail="El docente no pertenece a su departamento",
        )

    return ResponseSchema(
        status=200,
        message="Teacher history found",
        data=history,
        path=f"/improvement-plans/teacher/{teacher_id}/history",
    )


@router.post(
    "/",
    response_model=ImprovementPlanDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_plan(
    payload: ImprovementPlanCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Create a new improvement plan with its items."""

    try:
        plan = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400, message=str(e), path="/improvement-plans"
        )

    return ResponseSchema(
        status=201,
        message="Improvement plan created successfully",
        data=plan,
        path="/improvement-plans",
    )


@router.get(
    "/{plan_id}",
    response_model=ImprovementPlanDetailResponse,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def get_plan_by_id(
    plan_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Get an improvement plan by id. A DOCENTE can only see their own plan."""

    plan = await controller.get_by_id(plan_id)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}",
        )

    _ensure_can_access(controller, current_user, plan)

    return ResponseSchema(
        status=200,
        message="Improvement plan found",
        data=plan,
        path=f"/improvement-plans/{plan_id}",
    )


@router.put(
    "/{plan_id}",
    response_model=ImprovementPlanDetailResponse,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_plan(
    plan_id: int,
    payload: ImprovementPlanUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Update a plan and its items (add/remove/update)."""

    plan = await controller.update(plan_id, payload, current_user)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}",
        )

    return ResponseSchema(
        status=200,
        message="Improvement plan updated successfully",
        data=plan,
        path=f"/improvement-plans/{plan_id}",
    )


@router.post(
    "/{plan_id}/acta",
    response_model=ImprovementPlanDetailResponse,
    responses={
        400: {"model": ResponseSchema},
        403: {"description": "Forbidden"},
        404: {"model": ResponseSchema},
    },
)
async def upload_acta(
    plan_id: int,
    file: UploadFile | None = File(default=None),
    description: str | None = Form(default=None),
    current_user=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Attach or replace the acta de compromiso (PDF and/or description).

    The acta is optional at plan creation and editable while the plan is open."""

    plan = await controller.get_by_id(plan_id)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}/acta",
        )

    _ensure_can_access(controller, current_user, plan)

    if _is_closed(plan):
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar el acta de un plan cerrado",
        )

    if file is None and description is None:
        raise HTTPException(
            status_code=400,
            detail="Debe enviar un PDF y/o una descripción del acta",
        )

    file_url: str | None = None
    if file is not None:
        pdf_bytes = await _read_pdf(file)
        file_url = _save_plan_pdf(plan_id, pdf_bytes, "acta")

    result = await controller.set_acta(
        plan_id, current_user, file_url=file_url, description=description
    )

    _delete_upload(result.get("previous_file_url") if result else None)

    return ResponseSchema(
        status=200,
        message="Acta de compromiso guardada exitosamente",
        data=result["plan"] if result else None,
        path=f"/improvement-plans/{plan_id}/acta",
    )


@router.post(
    "/{plan_id}/evidences",
    response_model=ImprovementPlanDetailResponse,
    responses={
        400: {"model": ResponseSchema},
        403: {"description": "Forbidden"},
        404: {"model": ResponseSchema},
    },
    status_code=201,
)
async def add_evidence(
    plan_id: int,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    item_id: int | None = Form(default=None),
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Attach an evidence PDF to a plan, optionally tied to one of its items.

    The plan's teacher uploads proof of compliance; the director can also
    attach evidence collected during follow-up meetings."""

    plan = await controller.get_by_id(plan_id)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}/evidences",
        )

    _ensure_can_access(controller, current_user, plan)

    if _is_closed(plan):
        raise HTTPException(
            status_code=400,
            detail="No se pueden agregar evidencias a un plan cerrado",
        )

    pdf_bytes = await _read_pdf(file)
    file_url = _save_plan_pdf(plan_id, pdf_bytes, "evidence")

    try:
        updated = await controller.add_evidence(
            plan_id,
            current_user,
            file_url=file_url,
            description=description,
            item_id=item_id,
        )
    except ValueError as e:
        _delete_upload(file_url)
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseSchema(
        status=201,
        message="Evidencia agregada exitosamente",
        data=updated,
        path=f"/improvement-plans/{plan_id}/evidences",
    )


@router.delete(
    "/{plan_id}/evidences/{evidence_id}",
    response_model=ImprovementPlanDetailResponse,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def delete_evidence(
    plan_id: int,
    evidence_id: int,
    current_user=Depends(require_roles(ANY_ROLE)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Delete an evidence. Allowed to whoever uploaded it, or to the plan's
    director/admin."""

    plan = await controller.get_by_id(plan_id)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}/evidences/{evidence_id}",
        )

    _ensure_can_access(controller, current_user, plan)

    evidence = controller.get_evidence(plan_id, evidence_id)

    if not evidence:
        return ResponseSchema(
            status=404,
            message="Evidence not found",
            path=f"/improvement-plans/{plan_id}/evidences/{evidence_id}",
        )

    roles = set(current_user.get("roles", []))
    is_manager = RoleName.ADMIN.value in roles or (
        RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles
        and plan.get("department_id") == current_user.get("department_id")
    )

    if not is_manager and evidence.uploaded_by != current_user.get("id"):
        raise HTTPException(
            status_code=403,
            detail="Solo quien subió la evidencia (o el director) puede eliminarla",
        )

    result = await controller.delete_evidence(plan_id, evidence_id, current_user)

    _delete_upload(result.get("file_url") if result else None)

    return ResponseSchema(
        status=200,
        message="Evidencia eliminada exitosamente",
        data=result["plan"] if result else None,
        path=f"/improvement-plans/{plan_id}/evidences/{evidence_id}",
    )


@router.post(
    "/{plan_id}/close",
    response_model=ImprovementPlanDetailResponse,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def close_plan(
    plan_id: int,
    payload: ImprovementPlanClose,
    current_user=Depends(get_current_user),
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Close a plan (manual anytime, or confirming the verification result)."""

    plan = await controller.close(plan_id, payload, current_user)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}/close",
        )

    return ResponseSchema(
        status=200,
        message="Improvement plan closed successfully",
        data=plan,
        path=f"/improvement-plans/{plan_id}/close",
    )


@router.post(
    "/{plan_id}/evaluate",
    response_model=ImprovementPlanDetailResponse,
    responses={404: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def evaluate_plan(
    plan_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Recompute item compliance against the verification period and suggest a
    result (does not close the plan)."""

    plan = await controller.evaluate(plan_id, current_user)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}/evaluate",
        )

    return ResponseSchema(
        status=200,
        message="Improvement plan evaluated successfully",
        data=plan,
        path=f"/improvement-plans/{plan_id}/evaluate",
    )
