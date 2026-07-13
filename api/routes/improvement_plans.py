"""
Routes for improvement plan operations (Plan de Seguimiento Docente).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

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

router = APIRouter(prefix="/improvement-plans", tags=["Improvement Plans"])

DIRECTOR_OR_ADMIN = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


def _effective_department_id(
    current_user: dict, department_id: int | None
) -> int | None:
    """ADMIN may target any department via query; a director defaults to theirs."""

    if department_id is not None:
        return department_id
    return current_user.get("department_id")


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
    _=Depends(require_roles(DIRECTOR_OR_ADMIN)),
    controller: ImprovementPlansController = Depends(
        get_improvement_plans_controller
    ),
):
    """Get an improvement plan by id."""

    plan = await controller.get_by_id(plan_id)

    if not plan:
        return ResponseSchema(
            status=404,
            message="Improvement plan not found",
            path=f"/improvement-plans/{plan_id}",
        )

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
