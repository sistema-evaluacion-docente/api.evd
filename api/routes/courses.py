"""
Routes for course operations.
"""

from fastapi import Depends

from api.controllers.courses import CoursesController, get_courses_controller
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseListResponse,
    CourseUpdate,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/courses", tags=["Courses"])


@router.get(
    "/",
    response_model=CourseListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_courses(
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Endpoint to list all courses."""

    courses = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Courses found",
        data=courses,
        path="/courses",
    )


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_course_by_id(
    course_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Endpoint to get a course by ID."""

    course = await controller.get_by_id(course_id)

    if not course:
        return ResponseSchema(
            status=404,
            message="Course not found",
            path=f"/courses/{course_id}",
        )

    return ResponseSchema(
        status=200,
        message="Course found",
        data=course,
        path=f"/courses/{course_id}",
    )


@router.post(
    "/",
    response_model=CourseDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_course(
    payload: CourseCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Endpoint to create a new course."""

    try:
        course = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/courses",
        )

    return ResponseSchema(
        status=201,
        message="Course created successfully",
        data=course,
        path="/courses",
    )


@router.put(
    "/{course_id}",
    response_model=CourseDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: CoursesController = Depends(get_courses_controller),
):
    """Endpoint to update a course."""

    course = await controller.update(course_id, payload, current_user)

    if not course:
        return ResponseSchema(
            status=404,
            message="Course not found",
            path=f"/courses/{course_id}",
        )

    return ResponseSchema(
        status=200,
        message="Course updated successfully",
        data=course,
        path=f"/courses/{course_id}",
    )
