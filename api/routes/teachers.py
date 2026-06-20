"""
Routes for teacher operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.teachers import TeachersController, get_teachers_controller
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.response import ResponseSchema
from api.schemas.teacher import TeacherCreate, TeacherDetailResponse, TeacherListResponse, TeacherUpdate
from api.schemas.user import RoleName

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get(
    "/",
    response_model=TeacherListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_teachers(
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to list all teachers."""

    teachers = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Teachers found",
        data=teachers,
        path="/teachers",
    )


@router.get(
    "/{teacher_id}",
    response_model=TeacherDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_teacher_by_id(
    teacher_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to get a teacher by ID."""

    teacher = await controller.get_by_id(teacher_id)

    if not teacher:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            path=f"/teachers/{teacher_id}",
        )

    return ResponseSchema(
        status=200,
        message="Teacher found",
        data=teacher,
        path=f"/teachers/{teacher_id}",
    )


@router.post(
    "/",
    response_model=TeacherDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_teacher(
    payload: TeacherCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to create a new teacher."""

    try:
        teacher = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/teachers",
        )

    return ResponseSchema(
        status=201,
        message="Teacher created successfully",
        data=teacher,
        path="/teachers",
    )


@router.put(
    "/{teacher_id}",
    response_model=TeacherDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to update a teacher."""

    teacher = await controller.update(teacher_id, payload, current_user)

    if not teacher:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            path=f"/teachers/{teacher_id}",
        )

    return ResponseSchema(
        status=200,
        message="Teacher updated successfully",
        data=teacher,
        path=f"/teachers/{teacher_id}",
    )
