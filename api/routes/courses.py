"""
Routes for course operations.
"""

from fastapi import Depends, HTTPException

from api.controllers.courses import CoursesController, get_courses_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.course import (
    CourseCreate,
    CourseFiltersDep,
    CourseNameUpdate,
    CourseOut,
    CourseUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/courses", tags=["Courses"])

_ROLES = [RoleName.ADMIN]
_DIRECTOR_ROLES = [RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get("/", response_model=list[CourseOut])
async def get_all_courses(
    filters: CourseFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """List all courses with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.post("/", response_model=CourseOut, status_code=201)
async def create_course(
    payload: CourseCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Create a new course."""

    return await controller.create(payload, current_user)


@router.get("/{course_id}", response_model=CourseOut)
async def get_course_by_id(
    course_id: int,
    _=Depends(require_roles(_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Get a course by ID."""

    course = await controller.get_by_id(course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return course


@router.patch("/{course_id}/name", response_model=CourseOut)
async def patch_course_name(
    course_id: int,
    payload: CourseNameUpdate,
    current_user=Depends(require_roles(_DIRECTOR_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Update only the name of a course. Restricted to the director's own department."""

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    course = await controller.update_name(course_id, payload.name, department_id, current_user)

    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return course


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Update a course."""

    course = await controller.update(course_id, payload, current_user)

    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return course


@router.delete("/{course_id}", response_model=CourseOut)
async def delete_course(
    course_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Delete a course."""

    course = await controller.delete(course_id, current_user)

    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return course
