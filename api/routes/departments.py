"""Routes for department operations."""

from fastapi import Depends, HTTPException

from api.controllers.departments import (
    DepartmentsController,
    get_departments_controller,
)
from api.controllers.directors import (
    DirectorsController,
    get_directors_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.department import (
    AssignDirectorRequest,
    DepartmentCreate,
    DepartmentFiltersDep,
    DepartmentOut,
    DepartmentUpdate,
)
from api.schemas.director import DirectorOut
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/departments", tags=["Departments"])

_ROLES = [RoleName.ADMIN]


@router.get("/", response_model=list[DepartmentOut])
async def get_all_departments(
    filters: DepartmentFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_ROLES)),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """List all departments with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.get("/{department_id}", response_model=DepartmentOut)
async def get_department_by_id(
    department_id: int,
    _=Depends(require_roles(_ROLES)),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Get a department by ID."""

    department = await controller.get_by_id(department_id)

    if not department:
        raise HTTPException(status_code=404, detail="Departmento no encontrado")

    return department


@router.post("/", response_model=DepartmentOut, status_code=201)
async def create_department(
    payload: DepartmentCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Create a new department."""

    return await controller.create(payload, current_user)


@router.put("/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Update a department."""

    department = await controller.update(department_id, payload, current_user)

    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    return department


@router.delete("/{department_id}", response_model=DepartmentOut)
async def delete_department(
    department_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: DepartmentsController = Depends(get_departments_controller),
):
    """Delete a department."""

    department = await controller.delete(department_id, current_user)

    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    return department


@router.post("/{department_id}/director", response_model=DirectorOut)
async def assign_director(
    department_id: int,
    payload: AssignDirectorRequest,
    current_user=Depends(require_roles(_ROLES)),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Assign a director to a department."""

    try:
        director = await controller.assign_director(
            department_id, payload.user_id, current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return director


@router.delete("/{department_id}/director", status_code=204)
async def unassign_director(
    department_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Unassign the director from a department."""

    result = await controller.unassign_director(department_id, current_user)

    if not result:
        raise HTTPException(
            status_code=404, detail="Director no encontrado para este departamento"
        )

    return None
