"""
Routes for academic period operations.
"""

from fastapi import Depends, Query

from api.controllers.academic_periods import (
    AcademicPeriodsController,
    get_academic_periods_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodDetailResponse,
    AcademicPeriodOut,
    AcademicPeriodStatusUpdate,
    AcademicPeriodUpdate,
)
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/academic-periods", tags=["Academic Periods"])


@router.get(
    "/",
    response_model=list[AcademicPeriodOut],
    responses={403: {"description": "Forbidden"}},
)
async def get_all_academic_periods(
    search: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(
        require_roles(
            [
                RoleName.ADMIN,
                RoleName.DIRECTOR_DE_DEPARTAMENTO,
                RoleName.DOCENTE,
            ]
        )
    ),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to list all academic periods (any authenticated role)."""

    periods = await controller.get_all(search=search, page=page, limit=limit)

    if periods is None:
        return ResponseSchema(
            status=400,
            message="Error getting academic periods",
            path="/academic-periods",
        )

    return periods["items"]


@router.get(
    "/{period_id}",
    response_model=AcademicPeriodDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_academic_period_by_id(
    period_id: int,
    _=Depends(
        require_roles(
            [
                RoleName.ADMIN,
                RoleName.DIRECTOR_DE_DEPARTAMENTO,
                RoleName.DOCENTE,
            ]
        )
    ),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to get an academic period by ID (any authenticated role)."""

    period = await controller.get_by_id(period_id)

    if not period:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}",
        )

    return ResponseSchema(
        status=200,
        message="Academic period found",
        data=period,
        path=f"/academic-periods/{period_id}",
    )


@router.post(
    "/",
    response_model=AcademicPeriodDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_academic_period(
    payload: AcademicPeriodCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to create a new academic period."""

    try:
        period = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/academic-periods",
        )

    return ResponseSchema(
        status=201,
        message="Academic period created successfully",
        data=period,
        path="/academic-periods",
    )


@router.put(
    "/{period_id}",
    response_model=AcademicPeriodDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_academic_period(
    period_id: int,
    payload: AcademicPeriodUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to update an academic period."""

    period = await controller.update(period_id, payload, current_user)

    if not period:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}",
        )

    return ResponseSchema(
        status=200,
        message="Academic period updated successfully",
        data=period,
        path=f"/academic-periods/{period_id}",
    )


@router.patch(
    "/{period_id}/activate",
    response_model=AcademicPeriodDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def activate_academic_period(
    period_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to activate an academic period (deactivates any currently active one)."""

    period = await controller.activate(period_id, current_user)

    if not period:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}/activate",
        )

    return ResponseSchema(
        status=200,
        message="Academic period activated successfully",
        data=period,
        path=f"/academic-periods/{period_id}/activate",
    )


@router.patch(
    "/{period_id}/close",
    response_model=AcademicPeriodDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def close_academic_period(
    period_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to close the active academic period."""

    try:
        period = await controller.close(period_id, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path=f"/academic-periods/{period_id}/close",
        )

    if not period:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}/close",
        )

    return ResponseSchema(
        status=200,
        message="Academic period closed successfully",
        data=period,
        path=f"/academic-periods/{period_id}/close",
    )


@router.patch(
    "/{period_id}/status",
    response_model=AcademicPeriodDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_academic_period_status(
    period_id: int,
    payload: AcademicPeriodStatusUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to activate/deactivate an academic period."""

    period = await controller.update_status(period_id, payload, current_user)

    if not period:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}/status",
        )

    return ResponseSchema(
        status=200,
        message="Academic period status updated successfully",
        data=period,
        path=f"/academic-periods/{period_id}/status",
    )


@router.delete(
    "/{period_id}",
    response_model=None,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def delete_academic_period(
    period_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Endpoint to delete an academic period. Only allowed if no evaluations are associated."""

    try:
        deleted = await controller.delete(period_id, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path=f"/academic-periods/{period_id}",
        )

    if not deleted:
        return ResponseSchema(
            status=404,
            message="Academic period not found",
            path=f"/academic-periods/{period_id}",
        )

    return ResponseSchema(
        status=200,
        message="Academic period deleted successfully",
        data=None,
        path=f"/academic-periods/{period_id}",
    )
