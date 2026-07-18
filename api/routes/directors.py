"""Routes for director operations."""

from fastapi import Depends, HTTPException

from api.controllers.directors import (
    DirectorsController,
    get_directors_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.director import (
    DirectorCreate,
    DirectorFiltersDep,
    DirectorOut,
    DirectorUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/directors", tags=["Directors"])


@router.get("/", response_model=list[DirectorOut])
async def get_all_directors(
    filters: DirectorFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """List all directors with optional filters and pagination."""

    result = await controller.get_all(filters, pagination)
    return result["items"]


@router.get("/{director_id}", response_model=DirectorOut)
async def get_director_by_id(
    director_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Get a director by ID."""

    director = await controller.get_by_id(director_id)
    if not director:
        raise HTTPException(status_code=404, detail="Director not found")
    return director


@router.post("/", response_model=DirectorOut, status_code=201)
async def create_director(
    payload: DirectorCreate,
    current_user=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Create a new director with user and department information."""

    return await controller.create(payload, current_user)


@router.put("/{director_id}", response_model=DirectorOut)
async def update_director(
    director_id: int,
    payload: DirectorUpdate,
    current_user=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Update an existing director's information."""

    director = await controller.update(director_id, payload, current_user)

    if not director:
        raise HTTPException(status_code=404, detail="Director no encontrado")

    return director


@router.delete("/{director_id}", response_model=DirectorOut)
async def delete_director(
    director_id: int,
    current_user=Depends(require_roles([RoleName.ADMIN])),
    controller: DirectorsController = Depends(get_directors_controller),
):
    """Delete a director by ID."""

    director = await controller.delete(director_id, current_user)

    if not director:
        raise HTTPException(status_code=404, detail="Director no encontrado")

    return director
