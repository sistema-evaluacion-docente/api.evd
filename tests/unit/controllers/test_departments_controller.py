"""
Tests for DepartmentsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.departments import DepartmentsController
from api.core.pagination import PaginationParams
from api.schemas.department import (
    DepartmentCreate,
    DepartmentFilters,
    DepartmentUpdate,
)


class TestDepartmentsController:
    """Test suite for DepartmentsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock DepartmentService."""

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

        return DepartmentsController(mock_service)

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

        filters = DepartmentFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {"id": 1, "code": "CS", "name": "CS"}

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99}
        data = DepartmentCreate(code="CS", name="CS")
        mock_service.create.return_value = {"id": 1, "code": "CS", "name": "CS"}

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["code"] == "CS"

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99}
        data = DepartmentUpdate(name="New Name")
        mock_service.update.return_value = {"id": 1, "name": "New Name"}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None
