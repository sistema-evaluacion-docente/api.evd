"""
Routes for academic group operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.academic_groups import (
    AcademicGroupsController,
    get_academic_groups_controller,
)
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupDetailResponse,
    AcademicGroupListResponse,
    AcademicGroupUpdate,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = APIRouter(prefix="/academic-groups", tags=["Academic Groups"])


@router.get(
    "/",
    response_model=AcademicGroupListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_academic_groups(
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Endpoint to list all academic groups."""

    groups = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Academic groups found",
        data=groups,
        path="/academic-groups",
    )


@router.get(
    "/{group_id}",
    response_model=AcademicGroupDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_academic_group_by_id(
    group_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Endpoint to get an academic group by ID."""

    group = await controller.get_by_id(group_id)

    if not group:
        return ResponseSchema(
            status=404,
            message="Academic group not found",
            path=f"/academic-groups/{group_id}",
        )

    return ResponseSchema(
        status=200,
        message="Academic group found",
        data=group,
        path=f"/academic-groups/{group_id}",
    )


@router.post(
    "/",
    response_model=AcademicGroupDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_academic_group(
    payload: AcademicGroupCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Endpoint to create a new academic group."""

    try:
        group = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/academic-groups",
        )

    return ResponseSchema(
        status=201,
        message="Academic group created successfully",
        data=group,
        path="/academic-groups",
    )


@router.put(
    "/{group_id}",
    response_model=AcademicGroupDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_academic_group(
    group_id: int,
    payload: AcademicGroupUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AcademicGroupsController = Depends(get_academic_groups_controller),
):
    """Endpoint to update an academic group."""

    group = await controller.update(group_id, payload, current_user)

    if not group:
        return ResponseSchema(
            status=404,
            message="Academic group not found",
            path=f"/academic-groups/{group_id}",
        )

    return ResponseSchema(
        status=200,
        message="Academic group updated successfully",
        data=group,
        path=f"/academic-groups/{group_id}",
    )
