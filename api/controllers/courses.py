"""Courses controller — thin delegation to CourseService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.courses import get_course_service
from api.schemas.course import CourseCreate, CourseFilters, CourseUpdate
from api.services.course_service import CourseService


class CoursesController:
    """Controller for course-related operations."""

    def __init__(self, service: CourseService):
        self.service = service

    async def get_all(
        self,
        filters: CourseFilters,
        pagination: PaginationParams,
        department_id: int,
    ):
        """Retrieve the director's own department's courses, based on filters and pagination."""

        return await self.service.get_all(filters, pagination, department_id)

    async def get_by_id(self, course_id: int, department_id: int):
        """Retrieve a course by ID (director-scoped)."""

        return await self.service.get_by_id(course_id, department_id)

    async def create(self, data: CourseCreate, department_id: int, current_user: dict):
        """Create a new course (director-scoped)."""

        return await self.service.create(data, department_id, current_user)

    async def update(
        self, course_id: int, data: CourseUpdate, department_id: int, current_user: dict
    ):
        """Update a course (director-scoped)."""

        return await self.service.update(course_id, data, department_id, current_user)

    async def update_name(
        self, course_id: int, name: str, department_id: int, current_user: dict
    ):
        """Update only the course name (director-scoped)."""

        return await self.service.update_name(course_id, name, department_id, current_user)

    async def delete(self, course_id: int, department_id: int, current_user: dict):
        """Delete a course (director-scoped)."""

        return await self.service.delete(course_id, department_id, current_user)


def get_courses_controller(
    service: CourseService = Depends(get_course_service),
):
    """Dependency injection for CoursesController."""

    return CoursesController(service)
