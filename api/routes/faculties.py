"""
Routes for faculty operations.
"""

from fastapi import Depends, Query

from api.controllers.faculties import (
    FacultiesController,
    get_faculties_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.faculty import (
    FacultyCreate,
    FacultyDetailResponse,
    FacultyListResponse,
    FacultyUpdate,
)
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/faculties", tags=["Faculties"])


@router.get(
    "/",
    response_model=FacultyListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_faculties(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Endpoint to list all faculties."""

    faculties = await controller.get_all(search=search, page=page, limit=limit)

    return ResponseSchema(
        status=200,
        message="Faculties found",
        data=faculties["items"],
        pagination=Pagination(
            total=faculties["total"],
            page=faculties["page"],
            limit=faculties["limit"],
            pages=faculties["pages"],
        ),
        path="/faculties",
    )


@router.get(
    "/{faculty_id}",
    response_model=FacultyDetailResponse,
    responses={403: {"description": "Forbidden"},
               404: {"model": ResponseSchema}},
)
async def get_faculty_by_id(
    faculty_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Endpoint to get a faculty by ID."""

    faculty = await controller.get_by_id(faculty_id)

    if not faculty:
        return ResponseSchema(
            status=404,
            message="Faculty not found",
            path=f"/faculties/{faculty_id}",
        )

    return ResponseSchema(
        status=200,
        message="Faculty found",
        data=faculty,
        path=f"/faculties/{faculty_id}",
    )


@router.post(
    "/",
    response_model=FacultyDetailResponse,
    responses={400: {"model": ResponseSchema},
               403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_faculty(
    payload: FacultyCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Endpoint to create a new faculty."""

    try:
        faculty = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/faculties",
        )

    return ResponseSchema(
        status=201,
        message="Faculty created successfully",
        data=faculty,
        path="/faculties",
    )


@router.put(
    "/{faculty_id}",
    response_model=FacultyDetailResponse,
    responses={400: {"model": ResponseSchema},
               403: {"description": "Forbidden"}},
)
async def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: FacultiesController = Depends(get_faculties_controller),
):
    """Endpoint to update a faculty."""

    faculty = await controller.update(faculty_id, payload, current_user)

    if not faculty:
        return ResponseSchema(
            status=404,
            message="Faculty not found",
            path=f"/faculties/{faculty_id}",
        )

    return ResponseSchema(
        status=200,
        message="Faculty updated successfully",
        data=faculty,
        path=f"/faculties/{faculty_id}",
    )
