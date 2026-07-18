"""Teachers controller — thin delegation to TeacherService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.teachers import get_teacher_service
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)
from api.services.teacher_service import TeacherService


class TeachersController:
    """Controller for teacher-related operations."""

    def __init__(self, service: TeacherService):
        self.service = service

    async def get_all(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all teachers based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_all_with_averages(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
        academic_period_id: int,
    ):
        """Retrieve teachers with averages for a given academic period."""

        return await self.service.get_all_with_averages(
            filters, pagination, academic_period_id
        )

    async def get_by_id(self, teacher_id: int):
        """Retrieve a teacher by ID."""

        return await self.service.get_by_id(teacher_id)

    async def create(self, data: TeacherCreate, current_user: dict):
        """Create a new teacher."""

        return await self.service.create(data, current_user)

    async def create_with_user(self, data: TeacherCreateWithUser, current_user: dict):
        """Create a teacher with user information."""

        return await self.service.create_with_user(data, current_user)

    async def update(self, teacher_id: int, data: TeacherUpdate, current_user: dict):
        """Update a teacher."""

        return await self.service.update(teacher_id, data, current_user)

    async def delete(self, teacher_id: int, current_user: dict):
        """Delete a teacher."""

        return await self.service.delete(teacher_id, current_user)

    async def count_by_department(self, department_id: int, academic_period_id: int):
        """Count teachers in a department."""

        return await self.service.count_by_department(department_id, academic_period_id)

    async def get_history(self, teacher_id: int):
        """Get teacher's historical averages."""

        return await self.service.get_history(teacher_id)

    async def upload_excel(
        self, file_bytes: bytes, filename: str, department_id: int, current_user: dict
    ):
        """Bulk-upload teachers from an Excel/CSV file."""

        return await self.service.upload_excel(
            file_bytes, filename, department_id, current_user
        )


def get_teachers_controller(
    service: TeacherService = Depends(get_teacher_service),
):
    """Dependency injection for TeachersController."""

    return TeachersController(service)
