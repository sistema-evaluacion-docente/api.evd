"""
Routes for director operations.
"""

from fastapi import Depends, Query

from api.controllers.directors import (
    DirectorsController,
    get_directors_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.director import (
    DirectorCreate,
    DirectorDetailResponse,
    DirectorListResponse,
    DirectorUpdate,
)
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/directors", tags=["Directors"])


@router.get(
    "/",
    response_model=DirectorListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_directors(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Endpoint to list all directors."""

    directors = await controller.get_all(search=search, page=page, limit=limit)

    return ResponseSchema(
        status=200,
        message="Directors found",
        data=directors["items"],
        pagination=Pagination(
            total=directors["total"],
            page=directors["page"],
            limit=directors["limit"],
            pages=directors["pages"],
        ),
        path="/directors",
    )


@router.get(
    "/{director_id}",
    response_model=DirectorDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_director_by_id(
    director_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Endpoint to get a director by ID."""

    director = await controller.get_by_id(director_id)

    if not director:
        return ResponseSchema(
            status=404,
            message="Director not found",
            path=f"/directors/{director_id}",
        )

    return ResponseSchema(
        status=200,
        message="Director found",
        data=director,
        path=f"/directors/{director_id}",
    )


@router.post(
    "/",
    response_model=DirectorDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_director(
    payload: DirectorCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Endpoint to create a new director."""

    try:
        director = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/directors",
        )

    return ResponseSchema(
        status=201,
        message="Director created successfully",
        data=director,
        path="/directors",
    )


@router.put(
    "/{director_id}",
    response_model=DirectorDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_director(
    director_id: int,
    payload: DirectorUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Endpoint to update a director."""

    try:
        director = await controller.update(director_id, payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path=f"/directors/{director_id}",
        )

    if not director:
        return ResponseSchema(
            status=404,
            message="Director not found",
            path=f"/directors/{director_id}",
        )

    return ResponseSchema(
        status=200,
        message="Director updated successfully",
        data=director,
        path=f"/directors/{director_id}",
    )


@router.delete(
    "/{director_id}",
    response_model=DirectorDetailResponse,
    responses={403: {"description": "Forbidden"}},
)
async def delete_director(
    director_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Endpoint to delete a director."""

    director = await controller.delete(director_id, current_user)

    if not director:
        return ResponseSchema(
            status=404,
            message="Director not found",
            path=f"/directors/{director_id}",
        )

    return ResponseSchema(
        status=200,
        message="Director deleted successfully",
        data=director,
        path=f"/directors/{director_id}",
    )
