"""
Program routes module.
"""

from fastapi import Depends, HTTPException

from api.controllers.programs import ProgramsController, get_programs_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.program import (
    ProgramCreate,
    ProgramFiltersDep,
    ProgramOut,
    ProgramUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/programs", tags=["Programs"])


@router.get("/", response_model=list[ProgramOut])
async def get_all_programs(
    filters: ProgramFiltersDep,
    pagination: PaginationDep,
    _: bool = Depends(require_roles([RoleName.ADMIN])),
    controller: ProgramsController = Depends(get_programs_controller),
):
    """Get all programs with filters and pagination."""

    return await controller.get_all(filters, pagination)


@router.get("/{program_id}", response_model=ProgramOut)
async def get_program_by_id(
    program_id: int,
    _: bool = Depends(require_roles([RoleName.ADMIN])),
    controller: ProgramsController = Depends(get_programs_controller),
):
    """Get a program by ID."""

    program = await controller.get_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.post("/", response_model=ProgramOut, status_code=201)
async def create_program(
    data: ProgramCreate,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: ProgramsController = Depends(get_programs_controller),
):
    """Create a new program."""

    return await controller.create(data, current_user)


@router.put("/{program_id}", response_model=ProgramOut)
async def update_program(
    program_id: int,
    data: ProgramUpdate,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: ProgramsController = Depends(get_programs_controller),
):
    """Update a program."""

    program = await controller.update(program_id, data, current_user)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.delete("/{program_id}", response_model=ProgramOut)
async def delete_program(
    program_id: int,
    current_user: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: ProgramsController = Depends(get_programs_controller),
):
    """Delete a program."""

    program = await controller.delete(program_id, current_user)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program
