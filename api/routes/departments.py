"""
Routes for department operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.departments import (
    DepartmentsController,
    get_departments_controller,
)
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.department import (
    DepartmentCreate,
    DepartmentDetailResponse,
    DepartmentListResponse,
    DepartmentUpdate,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get(
    "/",
    response_model=DepartmentListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_departments(
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Endpoint to list all departments."""

    departments = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Departments found",
        data=departments,
        path="/departments",
    )


@router.get(
    "/{department_id}",
    response_model=DepartmentDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_department_by_id(
    department_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Endpoint to get a department by ID."""

    department = await controller.get_by_id(department_id)

    if not department:
        return ResponseSchema(
            status=404,
            message="Department not found",
            path=f"/departments/{department_id}",
        )

    return ResponseSchema(
        status=200,
        message="Department found",
        data=department,
        path=f"/departments/{department_id}",
    )


@router.post(
    "/",
    response_model=DepartmentDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_department(
    payload: DepartmentCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Endpoint to create a new department."""

    try:
        department = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/departments",
        )

    return ResponseSchema(
        status=201,
        message="Department created successfully",
        data=department,
        path="/departments",
    )


@router.put(
    "/{department_id}",
    response_model=DepartmentDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Endpoint to update a department."""

    department = await controller.update(department_id, payload, current_user)

    if not department:
        return ResponseSchema(
            status=404,
            message="Department not found",
            path=f"/departments/{department_id}",
        )

    return ResponseSchema(
        status=200,
        message="Department updated successfully",
        data=department,
        path=f"/departments/{department_id}",
    )
