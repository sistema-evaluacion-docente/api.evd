"""Controller for Director entity."""

from fastapi import Depends

from api.core.pagination import PaginationParams
from api.dependencies.directors import get_director_service
from api.schemas.director import DirectorCreate, DirectorFilters, DirectorUpdate
from api.services.director_service import DirectorService


class DirectorsController:
    """Controller to manage director operations."""

    def __init__(self, service: DirectorService):
        self.service = service

    async def get_all(
        self, filters: DirectorFilters, pagination: PaginationParams
    ) -> dict:
        """Get all directors with optional filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, director_id: int) -> dict | None:
        """Get a director by ID."""

        return await self.service.get_by_id(director_id)

    async def create(self, data: DirectorCreate, current_user: dict) -> dict:
        """Create a new director with user and department information."""

        return await self.service.create(data, current_user)

    async def update(
        self, director_id: int, data: DirectorUpdate, current_user: dict
    ) -> dict | None:
        """Update a director's information."""

        return await self.service.update(director_id, data, current_user)

    async def delete(self, director_id: int, current_user: dict) -> dict | None:
        """Delete a director by ID."""

        return await self.service.delete(director_id, current_user)

    async def assign_director(
        self, department_id: int, user_id: int, current_user: dict
    ) -> dict:
        """Assign a director to a department."""

        return await self.service.assign_director(department_id, user_id, current_user)

    async def unassign_director(
        self, department_id: int, current_user: dict
    ) -> dict | None:
        """Unassign the director from a department."""

        return await self.service.unassign_director(department_id, current_user)


def get_directors_controller(
    service: DirectorService = Depends(get_director_service),
) -> DirectorsController:
    """Dependency to get DirectorsController with injected DirectorService."""

    return DirectorsController(service)
