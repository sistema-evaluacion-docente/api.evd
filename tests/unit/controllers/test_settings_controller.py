"""Tests for SettingsController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.settings import SettingsController
from api.core.pagination import PaginationParams
from api.schemas.setting import (
    SettingCreate,
    SettingFilters,
    SettingUpdate,
)


class TestSettingsController:
    """Test suite for SettingsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock SettingService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.get_by_key = AsyncMock()
        service.create = AsyncMock()
        service.update = AsyncMock()
        service.delete = AsyncMock()
        service.get_history = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return SettingsController(mock_service)

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

        filters = SettingFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {"id": 1, "key": "app_name", "value": "My App"}

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_key_delegates_to_service(self, controller, mock_service):
        """Test get_by_key delegates to service."""

        mock_service.get_by_key.return_value = {"id": 1, "key": "app_name", "value": "My App"}

        result = await controller.get_by_key("app_name")

        mock_service.get_by_key.assert_called_once_with("app_name")
        assert result["key"] == "app_name"

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99, "uid": "test-uid"}
        data = SettingCreate(key="app_name", value="My App")
        mock_service.create.return_value = {"id": 1, "key": "app_name", "value": "My App"}

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["key"] == "app_name"

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99, "uid": "test-uid"}
        data = SettingUpdate(value="New Value")
        mock_service.update.return_value = {"id": 1, "key": "app_name", "value": "New Value"}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["value"] == "New Value"

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99, "uid": "test-uid"}
        mock_service.delete.return_value = {"id": 1, "key": "app_name"}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_service(self, controller, mock_service):
        """Test get_history delegates to service."""

        mock_service.get_history.return_value = {
            "items": [],
            "total": 0,
        }

        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_history(key="app_name", pagination=pagination)

        mock_service.get_history.assert_called_once_with("app_name", pagination)
        assert result["total"] == 0
