"""
Routes for teacher operations.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from api.controllers.teachers import TeachersController, get_teachers_controller
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.teacher import (
    BulkUploadResult,
    TeacherBulkUploadResponse,
    TeacherCreate,
    TeacherDetailResponse,
    TeacherListResponse,
    TeacherUpdate,
)
from api.schemas.evaluation_summary import TeacherHistoryResponse
from api.schemas.user import RoleName
from api.utils.file_validation import validate_file_size

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.post(
    "/upload",
    response_model=TeacherBulkUploadResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def upload_teachers_excel(
    file: UploadFile = File(...),
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Upload an Excel file to bulk-create teachers for the director's department.

    The Excel must have columns: nombre, email, codigo institucional, tipo de contrato.
    """

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un Excel (.xlsx o .xls)",
        )

    file_bytes = await file.read()

    validate_file_size(file_bytes)

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="El archivo está vacío",
        )

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    try:
        result = await controller.upload_excel(file_bytes, department_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseSchema(
        status=201,
        message=(
            f"Importación completada: {len(result['created'])} creados, "
            f"{len(result['skipped'])} omitidos, {len(result['errors'])} errores"
        ),
        data=BulkUploadResult(**result),
        path="/teachers/upload",
    )


@router.get(
    "/",
    response_model=TeacherListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_teachers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(
        None,
        description="Search term for institutional code, name, email or contract type",
    ),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to list all teachers with pagination and search."""

    teachers, total = await controller.get_all(page=page, limit=limit, search=search)

    pages = (total + limit - 1) // limit if total else 0

    return ResponseSchema(
        status=200,
        message="Teachers found",
        data=teachers,
        pagination=Pagination(total=total, page=page, limit=limit, pages=pages),
        path="/teachers",
    )


@router.get(
    "/count",
    response_model=ResponseSchema,
    responses={403: {"description": "Forbidden"}},
)
async def count_teachers(
    academic_period_id: int = Query(..., description="Academic period ID"),
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Get the count of teachers in the director's department for current and previous period."""

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    count = await controller.count_by_department(department_id, academic_period_id)

    return ResponseSchema(
        status=200,
        message="Teacher count retrieved successfully",
        data={
            "current_count": count["current_count"],
            "previous_count": count["previous_count"],
            "department_id": department_id,
            "academic_period_id": academic_period_id,
        },
        path="/teachers/count",
    )


@router.get(
    "/{teacher_id}/history",
    response_model=TeacherHistoryResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_teacher_history(
    teacher_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Return the historical average score of a teacher across all evaluated periods."""

    history = await controller.get_history(teacher_id)

    if not history:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            path=f"/teachers/{teacher_id}/history",
        )

    return ResponseSchema(
        status=200,
        message="Teacher history retrieved successfully",
        data=history,
        path=f"/teachers/{teacher_id}/history",
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


@router.delete(
    "/{teacher_id}",
    response_model=TeacherDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def delete_teacher(
    teacher_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Endpoint to delete a teacher."""

    try:
        teacher = await controller.delete(teacher_id, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path=f"/teachers/{teacher_id}",
        )

    if not teacher:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            path=f"/teachers/{teacher_id}",
        )

    return ResponseSchema(
        status=200,
        message="Teacher deleted successfully",
        data=teacher,
        path=f"/teachers/{teacher_id}",
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
