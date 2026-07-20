"""Routes for academic period operations."""

from fastapi import Depends, HTTPException

from api.controllers.academic_periods import (
    AcademicPeriodsController,
    get_academic_periods_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodFiltersDep,
    AcademicPeriodOut,
    AcademicPeriodUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/academic-periods", tags=["Academic Periods"])

_ROLES = [RoleName.ADMIN]
_READ_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO, RoleName.DOCENTE]


@router.get("/", response_model=list[AcademicPeriodOut])
async def get_all_academic_periods(
    filters: AcademicPeriodFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_READ_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """List all academic periods with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.get("/{period_id}", response_model=AcademicPeriodOut)
async def get_academic_period_by_id(
    period_id: int,
    _=Depends(require_roles(_READ_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Get an academic period by ID."""

    period = await controller.get_by_id(period_id)

    if not period:
        raise HTTPException(status_code=404, detail="Periodo académico no encontrado")

    return period


@router.post("/", response_model=AcademicPeriodOut, status_code=201)
async def create_academic_period(
    payload: AcademicPeriodCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Create a new academic period."""

    return await controller.create(payload, current_user)


@router.put("/{period_id}", response_model=AcademicPeriodOut)
async def update_academic_period(
    period_id: int,
    payload: AcademicPeriodUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Update an academic period."""

    period = await controller.update(period_id, payload, current_user)

    if not period:
        raise HTTPException(status_code=404, detail="Periodo académico no encontrado")

    return period


@router.patch("/{period_id}/activate", response_model=AcademicPeriodOut)
async def activate_academic_period(
    period_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Activate an academic period. Fails if another period is already active."""

    period = await controller.activate(period_id, current_user)

    if not period:
        raise HTTPException(status_code=404, detail="Periodo académico no encontrado")

    return period


@router.patch("/{period_id}/close", response_model=AcademicPeriodOut)
async def close_academic_period(
    period_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Close the active academic period."""

    period = await controller.close(period_id, current_user)

    if not period:
        raise HTTPException(status_code=404, detail="Periodo académico no encontrado")

    return period


@router.delete("/{period_id}", response_model=AcademicPeriodOut)
async def delete_academic_period(
    period_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicPeriodsController = Depends(get_academic_periods_controller),
):
    """Delete an academic period. Only allowed if no evaluations are associated."""

    period = await controller.delete(period_id, current_user)

    if not period:
        raise HTTPException(status_code=404, detail="Periodo académico no encontrado")

    return period
