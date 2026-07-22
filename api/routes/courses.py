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
    CourseOut,
    CourseUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/courses", tags=["Courses"])

_ROLES = [RoleName.ADMIN]


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
