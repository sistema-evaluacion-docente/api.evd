"""
Program controller module.
"""

from fastapi import Depends

from api.core.pagination import PaginationParams
from api.dependencies.programs import get_program_service
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate
from api.services.program_service import ProgramService


class ProgramsController:
    """Controller for Program operations."""

    def __init__(self, service: ProgramService):
        self.service = service

    async def get_all(
        self, filters: ProgramFilters, pagination: PaginationParams
    ) -> dict:
        """Get all programs with filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, program_id: int) -> dict | None:
        """Get a program by ID."""

        return await self.service.get_by_id(program_id)

    async def create(self, data: ProgramCreate, current_user: dict) -> dict:
        """Create a new program."""

        return await self.service.create(data, current_user)

    async def update(
        self, program_id: int, data: ProgramUpdate, current_user: dict
    ) -> dict | None:
        """Update a program."""

        return await self.service.update(program_id, data, current_user)

    async def delete(self, program_id: int, current_user: dict) -> dict | None:
        """Delete a program."""

        return await self.service.delete(program_id, current_user)


def get_programs_controller(
    service: ProgramService = Depends(get_program_service),
) -> ProgramsController:
    """Get programs controller instance."""

    return ProgramsController(service)
