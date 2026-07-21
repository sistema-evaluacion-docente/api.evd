"""Tests for CoursesController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.courses import CoursesController
from api.core.pagination import PaginationParams
from api.schemas.course import CourseCreate, CourseFilters, CourseUpdate


class TestCoursesController:
    """Test suite for CoursesController."""

    @pytest.fixture
    def mock_service(self):
        """Mock CourseService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.create = AsyncMock()
        service.update = AsyncMock()
        service.delete = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return CoursesController(mock_service)

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_service(self, controller, mock_service):
        """Test get_all delegates to service."""

        mock_service.get_all.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = CourseFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {"id": 1, "code": "MATH101"}

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99}
        data = CourseCreate(code="MATH101", name="Cálculo I", department_id=5)
        mock_service.create.return_value = {"id": 1, "code": "MATH101"}

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99}
        data = CourseUpdate(name="Cálculo II")
        mock_service.update.return_value = {"id": 1, "name": "Cálculo II"}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["name"] == "Cálculo II"

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1, "code": "MATH101"}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result["id"] == 1
