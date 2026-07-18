"""
Faculty routes module.
"""

from fastapi import Depends, HTTPException

from api.controllers.faculties import FacultiesController, get_faculties_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.faculty import (
    FacultyCreate,
    FacultyFiltersDep,
    FacultyOut,
    FacultyUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/faculties", tags=["Faculties"])


@router.get("/", response_model=list[FacultyOut])
async def get_all_faculties(
    filters: FacultyFiltersDep,
    pagination: PaginationDep,
    _: bool = Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Get all faculties with filters and pagination."""

    result = await controller.get_all(filters, pagination)
    return result["items"]


@router.get("/{faculty_id}", response_model=FacultyOut)
async def get_faculty_by_id(
    faculty_id: int,
    _: bool = Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Get a faculty by ID."""

    faculty = await controller.get_by_id(faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


@router.post("/", response_model=FacultyOut, status_code=201)
async def create_faculty(
    data: FacultyCreate,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Create a new faculty."""

    return await controller.create(data, current_user)


@router.put("/{faculty_id}", response_model=FacultyOut)
async def update_faculty(
    faculty_id: int,
    data: FacultyUpdate,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Update a faculty."""

    faculty = await controller.update(faculty_id, data, current_user)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


@router.delete("/{faculty_id}", response_model=FacultyOut)
async def delete_faculty(
    faculty_id: int,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Delete a faculty."""

    faculty = await controller.delete(faculty_id, current_user)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty
