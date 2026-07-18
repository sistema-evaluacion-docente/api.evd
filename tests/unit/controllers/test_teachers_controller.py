"""
Tests for TeachersController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.teachers import TeachersController
from api.core.pagination import PaginationParams
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)


class TestTeachersController:
    """Test suite for TeachersController."""

    @pytest.fixture
    def mock_service(self):
        """Mock TeacherService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_all_with_averages = AsyncMock()
        service.get_by_id = AsyncMock()
        service.create = AsyncMock()
        service.create_with_user = AsyncMock()
        service.update = AsyncMock()
        service.delete = AsyncMock()
        service.count_by_department = AsyncMock()
        service.get_history = AsyncMock()
        service.upload_excel = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return TeachersController(mock_service)

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

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_all_with_averages_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_all_with_averages delegates to service."""

        mock_service.get_all_with_averages.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all_with_averages(filters, pagination, 1)

        mock_service.get_all_with_averages.assert_called_once_with(
            filters, pagination, 1
        )

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {"id": 1, "institutional_code": "12345"}

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99}
        data = TeacherCreate(institutional_code="12345")
        mock_service.create.return_value = {"id": 1, "institutional_code": "12345"}

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["institutional_code"] == "12345"

    @pytest.mark.asyncio
    async def test_create_with_user_delegates_to_service(
        self, controller, mock_service
    ):
        """Test create_with_user delegates to service."""

        current_user = {"id": 99}
        data = TeacherCreateWithUser(
            email="test@example.com",
            name="Test",
            institutional_code="12345",
        )
        mock_service.create_with_user.return_value = {
            "id": 1,
            "institutional_code": "12345",
        }

        result = await controller.create_with_user(data, current_user)

        mock_service.create_with_user.assert_called_once_with(data, current_user)

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99}
        data = TeacherUpdate(contract_type="PART_TIME")
        mock_service.update.return_value = {"id": 1, "contract_type": "PART_TIME"}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["contract_type"] == "PART_TIME"

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None

    @pytest.mark.asyncio
    async def test_count_by_department_delegates_to_service(
        self, controller, mock_service
    ):
        """Test count_by_department delegates to service."""

        mock_service.count_by_department.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await controller.count_by_department(1, 1)

        mock_service.count_by_department.assert_called_once_with(1, 1)
        assert result["current_count"] == 10

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_service(self, controller, mock_service):
        """Test get_history delegates to service."""

        mock_service.get_history.return_value = {
            "teacher_id": 1,
            "history": [],
        }

        result = await controller.get_history(1)

        mock_service.get_history.assert_called_once_with(1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_upload_excel_delegates_to_service(self, controller, mock_service):
        """Test upload_excel delegates to service."""

        current_user = {"id": 99}
        mock_service.upload_excel.return_value = {
            "created": [],
            "skipped": [],
            "errors": [],
        }

        result = await controller.upload_excel(b"", "test.xlsx", 1, current_user)

        mock_service.upload_excel.assert_called_once_with(
            b"", "test.xlsx", 1, current_user
        )
        assert "created" in result
