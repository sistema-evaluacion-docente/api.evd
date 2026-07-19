"""Tests for DirectorsController."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.directors import DirectorsController
from api.core.pagination import PaginationParams
from api.schemas.director import DirectorCreate, DirectorFilters, DirectorUpdate


class TestDirectorsController:
    """Test suite for DirectorsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock DirectorService."""
        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.create = AsyncMock()
        service.update = AsyncMock()
        service.delete = AsyncMock()
        service.assign_director = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""
        return DirectorsController(mock_service)

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

        filters = DirectorFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""
        mock_service.get_by_id.return_value = {
            "id": 1,
            "user_id": 10,
            "department_id": 1,
        }

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""
        current_user = {"id": 99}
        data = DirectorCreate(email="test@example.com", name="Test", department_id=1)
        mock_service.create.return_value = {"id": 1, "user_id": 10, "department_id": 1}

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""
        current_user = {"id": 99}
        data = DirectorUpdate(active=False)
        mock_service.update.return_value = {"id": 1, "active": False}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["active"] is False

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""
        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None

    @pytest.mark.asyncio
    async def test_assign_director_delegates_to_service(self, controller, mock_service):
        """Test assign_director delegates to service."""
        current_user = {"id": 99}
        mock_service.assign_director.return_value = {
            "id": 1,
            "user_id": 10,
            "department_id": 1,
        }

        result = await controller.assign_director(1, 10, current_user)

        mock_service.assign_director.assert_called_once_with(1, 10, current_user)
        assert result["id"] == 1
