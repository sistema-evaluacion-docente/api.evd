"""
Routes for academic group operations.
"""

from fastapi import Depends, HTTPException

from api.controllers.academic_groups import (
    AcademicGroupsController,
    get_academic_groups_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupFiltersDep,
    AcademicGroupOut,
    AcademicGroupUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/academic-groups", tags=["Academic Groups"])

_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get("/", response_model=list[AcademicGroupOut])
async def get_all_academic_groups(
    filters: AcademicGroupFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_ROLES)),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """List all academic groups with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.post("/", response_model=AcademicGroupOut, status_code=201)
async def create_academic_group(
    payload: AcademicGroupCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Create a new academic group."""

    return await controller.create(payload, current_user)


@router.get("/{group_id}", response_model=AcademicGroupOut)
async def get_academic_group_by_id(
    group_id: int,
    _=Depends(require_roles(_ROLES)),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Get an academic group by ID."""

    group = await controller.get_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=404, detail="El grupo académico no fue encontrado"
        )

    return group


@router.put("/{group_id}", response_model=AcademicGroupOut)
async def update_academic_group(
    group_id: int,
    payload: AcademicGroupUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Update an academic group."""

    group = await controller.update(group_id, payload, current_user)

    if not group:
        raise HTTPException(
            status_code=404, detail="El grupo académico no fue encontrado"
        )

    return group


@router.delete("/{group_id}", response_model=AcademicGroupOut)
async def delete_academic_group(
    group_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Delete an academic group."""

    group = await controller.delete(group_id, current_user)

    if not group:
        raise HTTPException(
            status_code=404, detail="El grupo académico no fue encontrado"
        )

    return group
