"""Departments controller — thin delegation to DepartmentService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.departments import get_department_service
from api.schemas.department import (
    DepartmentCreate,
    DepartmentFilters,
    DepartmentUpdate,
)
from api.services.department_service import DepartmentService


class DepartmentsController:
    """Controller for department-related operations."""

    def __init__(self, service: DepartmentService):
        self.service = service

    async def get_all(
        self,
        filters: DepartmentFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all departments based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, department_id: int):
        """Retrieve a department by ID."""

        return await self.service.get_by_id(department_id)

    async def create(self, data: DepartmentCreate, current_user: dict):
        """Create a new department."""

        return await self.service.create(data, current_user)

    async def update(
        self, department_id: int, data: DepartmentUpdate, current_user: dict
    ):
        """Update a department."""

        return await self.service.update(department_id, data, current_user)

    async def delete(self, department_id: int, current_user: dict):
        """Delete a department."""

        return await self.service.delete(department_id, current_user)


def get_departments_controller(
    service: DepartmentService = Depends(get_department_service),
):
    """Dependency injection for DepartmentsController."""

    return DepartmentsController(service)
