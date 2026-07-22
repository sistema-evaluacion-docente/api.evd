"""Academic groups controller — thin delegation to AcademicGroupService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.academic_groups import get_academic_group_service
from api.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupFilters,
    AcademicGroupUpdate,
)
from api.services.academic_group_service import AcademicGroupService


class AcademicGroupsController:
    """Controller for academic group-related operations."""

    def __init__(self, service: AcademicGroupService):
        self.service = service

    async def get_all(
        self,
        filters: AcademicGroupFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all academic groups based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, group_id: int):
        """Retrieve an academic group by ID."""

        return await self.service.get_by_id(group_id)

    async def create(self, data: AcademicGroupCreate, current_user: dict):
        """Create a new academic group."""

        return await self.service.create(data, current_user)

    async def update(
        self, group_id: int, data: AcademicGroupUpdate, current_user: dict
    ):
        """Update an academic group."""

        return await self.service.update(group_id, data, current_user)

    async def delete(self, group_id: int, current_user: dict):
        """Delete an academic group."""

        return await self.service.delete(group_id, current_user)


def get_academic_groups_controller(
    service: AcademicGroupService = Depends(get_academic_group_service),
):
    """Dependency injection for AcademicGroupsController."""

    return AcademicGroupsController(service)
