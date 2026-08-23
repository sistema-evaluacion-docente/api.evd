"""Routes for teacher operations."""

import io

from fastapi import Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from api.controllers.teachers import TeachersController, get_teachers_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.academic_group import Modality
from api.schemas.evaluation_summary import (
    CourseHistoryOut,
    TeacherDashboardOut,
    TeacherHistoryOut,
)
from api.schemas.teacher import (
    BulkUploadResult,
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFiltersDep,
    TeacherOut,
    TeacherUpdate,
)
from api.schemas.pagination import build_paginated_response
from api.schemas.user import RoleName
from api.utils.file_validation import validate_file_size

router = EnvelopeRouter(prefix="/teachers", tags=["Teachers"])

_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get("/", response_model=list[TeacherOut])
async def get_all_teachers(
    filters: TeacherFiltersDep,
    pagination: PaginationDep,
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """List all teachers with pagination and filters.

    Directors are restricted to their own department — any client-supplied
    department_id is ignored and replaced by the one from the token.
    """

    if RoleName.DIRECTOR_DE_DEPARTAMENTO in current_user.get("roles", []):
        department_id = current_user.get("department_id")
        if not department_id:
            return build_paginated_response([], 0, pagination)
        filters.department_id = department_id

    return await controller.get_all(filters, pagination)


@router.post("/", response_model=TeacherOut, status_code=201)
async def create_teacher(
    payload: TeacherCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Create a new teacher."""

    return await controller.create(payload, current_user)


@router.post("/with-user", response_model=TeacherOut, status_code=201)
async def create_teacher_with_user(
    payload: TeacherCreateWithUser,
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Create a new teacher with user information."""

    return await controller.create_with_user(payload, current_user)


@router.post("/upload", response_model=BulkUploadResult, status_code=201)
async def upload_teachers_excel(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Upload an Excel or CSV file to bulk-create teachers."""

    if not file.filename or not file.filename.lower().endswith(
        (".xlsx", ".xls", ".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un Excel (.xlsx, .xls) o CSV (.csv)",
        )

    file_bytes = await file.read()
    validate_file_size(file_bytes, 5)

    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    return await controller.upload_excel(
        file_bytes, file.filename, department_id, current_user
    )


@router.get("/with-averages", response_model=list[TeacherOut])
async def get_teachers_with_averages(
    filters: TeacherFiltersDep,
    pagination: PaginationDep,
    academic_period_id: int = Query(
        ..., description="Academic period ID to compute overall_average"
    ),
    has_average: bool = Query(
        True, description="Filter teachers that have an overall average or not"
    ),
    modality: Modality | None = Query(
        default=None,
        description=(
            "Calcular el promedio y los comentarios de alto riesgo solo con "
            "los grupos de esta modalidad. Sin el filtro se toman todos."
        ),
    ),
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """List teachers with overall_average for a given academic period.

    Directors are restricted to their own department — any client-supplied
    department_id is ignored and replaced by the one from the token.

    With `modality`, the average and the high-risk comment count cover only
    that kind of program, and teachers who do not teach in it drop out of the
    listing (unless `has_average` is false).
    """

    if RoleName.DIRECTOR_DE_DEPARTAMENTO in current_user.get("roles", []):
        department_id = current_user.get("department_id")
        if not department_id:
            return build_paginated_response([], 0, pagination)
        filters.department_id = department_id

    return await controller.get_all_with_averages(
        filters, pagination, academic_period_id, has_average, modality
    )


@router.get("/count")
async def count_teachers(
    academic_period_id: int = Query(..., description="Academic period ID"),
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Get the count of teachers in a department for current and previous period."""

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    return await controller.count_by_department(department_id, academic_period_id)


@router.get("/{teacher_id}/courses/{course_code}/history", response_model=CourseHistoryOut)
async def get_teacher_course_history(
    teacher_id: int,
    course_code: str,
    limit: int | None = Query(default=None, ge=1, description="Máximo de periodos a retornar"),
    current_user=Depends(get_current_user),
    _=Depends(
        require_roles(
            [RoleName.DOCENTE, RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]
        )
    ),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Return per-period score history for a teacher's course, with dimensions and department average."""

    result = await controller.get_course_history(
        current_user, teacher_id, course_code, limit
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get("/{teacher_id}/history", response_model=TeacherHistoryOut)
async def get_teacher_history(
    teacher_id: int,
    filters: TeacherFiltersDep,
    pagination: PaginationDep,
    current_user=Depends(get_current_user),
    _=Depends(
        require_roles(
            [RoleName.DOCENTE, RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]
        )
    ),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Return the historical average score of a teacher across all evaluated periods."""

    history = await controller.get_history(
        current_user, teacher_id, pagination, filters.sort_by
    )

    if not history:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return history


@router.get("/{teacher_id}/dashboard", response_model=TeacherDashboardOut)
async def get_teacher_dashboard(
    teacher_id: int,
    period_name: str = Query(..., description="Academic period name"),
    department_id: int = Query(..., description="Department ID"),
    _=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Get combined dashboard data for a teacher (evaluation detail, period comparison, comments, matrix)."""

    result = await controller.get_dashboard(teacher_id, period_name, department_id)

    if not result:
        raise HTTPException(
            status_code=404, detail="Docente o evaluación no encontrada"
        )

    return result


@router.get(
    "/{teacher_id}/evaluations/{evaluation_id}/report",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def download_teacher_evaluation_report(
    teacher_id: int,
    evaluation_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.DOCENTE, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Download the teacher's pages from an evaluation PDF.

    DOCENTE may only download their own report; DIRECTOR may download any
    teacher's report within their department."""

    pdf_bytes = await controller.get_evaluation_report(
        teacher_id, evaluation_id, current_user
    )

    if pdf_bytes is None:
        raise HTTPException(
            status_code=404,
            detail="Reporte no encontrado o el docente no aparece en esta evaluación",
        )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="evaluacion_docente_{teacher_id}.pdf"'
        },
    )


@router.get("/{teacher_id}", response_model=TeacherOut)
async def get_teacher_by_id(
    teacher_id: int,
    _=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Get a teacher by ID."""

    teacher = await controller.get_by_id(teacher_id)

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return teacher


@router.put("/{teacher_id}", response_model=TeacherOut)
async def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Update a teacher."""

    teacher = await controller.update(teacher_id, payload, current_user)

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return teacher


@router.delete("/{teacher_id}", response_model=TeacherOut)
async def delete_teacher(
    teacher_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: TeachersController = Depends(get_teachers_controller),
):
    """Delete a teacher."""

    teacher = await controller.delete(teacher_id, current_user)

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return teacher
