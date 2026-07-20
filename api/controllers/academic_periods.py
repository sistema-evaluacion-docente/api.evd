"""Academic periods controller — thin delegation to AcademicPeriodService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.academic_periods import get_academic_period_service
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodFilters,
    AcademicPeriodUpdate,
)
from api.services.academic_period_service import AcademicPeriodService


class AcademicPeriodsController:
    """Controller for academic period-related operations."""

    def __init__(self, service: AcademicPeriodService):
        self.service = service

    async def get_all(
        self,
        filters: AcademicPeriodFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all academic periods based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, period_id: int):
        """Retrieve an academic period by ID."""

        return await self.service.get_by_id(period_id)

    async def create(self, data: AcademicPeriodCreate, current_user: dict):
        """Create a new academic period."""

        return await self.service.create(data, current_user)

    async def update(
        self, period_id: int, data: AcademicPeriodUpdate, current_user: dict
    ):
        """Update an academic period."""

        return await self.service.update(period_id, data, current_user)

    async def activate(self, period_id: int, current_user: dict):
        """Activate an academic period."""

        return await self.service.activate(period_id, current_user)

    async def close(self, period_id: int, current_user: dict):
        """Close an academic period."""

        return await self.service.close(period_id, current_user)

    async def delete(self, period_id: int, current_user: dict):
        """Delete an academic period."""

        return await self.service.delete(period_id, current_user)


def get_academic_periods_controller(
    service: AcademicPeriodService = Depends(get_academic_period_service),
):
    """Dependency injection for AcademicPeriodsController."""

    return AcademicPeriodsController(service)
