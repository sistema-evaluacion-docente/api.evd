"""
Faculty controller module.
"""

from fastapi import Depends

from api.core.pagination import PaginationParams
from api.dependencies.faculties import get_faculty_service
from api.schemas.faculty import FacultyCreate, FacultyFilters, FacultyUpdate
from api.services.faculty_service import FacultyService


class FacultiesController:
    """Controller for Faculty operations."""

    def __init__(self, service: FacultyService):
        self.service = service

    async def get_all(
        self, filters: FacultyFilters, pagination: PaginationParams
    ) -> dict:
        """Get all faculties with filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, faculty_id: int) -> dict | None:
        """Get a faculty by ID."""

        return await self.service.get_by_id(faculty_id)

    async def create(self, data: FacultyCreate, current_user: dict) -> dict:
        """Create a new faculty."""

        return await self.service.create(data, current_user)

    async def update(
        self, faculty_id: int, data: FacultyUpdate, current_user: dict
    ) -> dict | None:
        """Update a faculty."""

        return await self.service.update(faculty_id, data, current_user)

    async def delete(self, faculty_id: int, current_user: dict) -> dict | None:
        """Delete a faculty."""

        return await self.service.delete(faculty_id, current_user)


def get_faculties_controller(
    service: FacultyService = Depends(get_faculty_service),
) -> FacultiesController:
    """Get faculties controller instance."""

    return FacultiesController(service)
