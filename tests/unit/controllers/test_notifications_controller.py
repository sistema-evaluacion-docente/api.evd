"""
Tests for NotificationsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.notifications import NotificationsController
from api.core.pagination import PaginationParams
from api.schemas.notification import (
    NotificationCreate,
    NotificationFilters,
    NotificationType,
)


class TestNotificationsController:
    """Test suite for NotificationsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock NotificationService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_unread_count = AsyncMock()
        service.create = AsyncMock()
        service.mark_as_read = AsyncMock()
        service.mark_all_as_read = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return NotificationsController(mock_service)

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

        filters = NotificationFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(
            user_id=10, filters=filters, pagination=pagination
        )

        mock_service.get_all.assert_called_once_with(10, filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_unread_count_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_unread_count delegates to service."""

        mock_service.get_unread_count.return_value = 5

        result = await controller.get_unread_count(user_id=10)

        mock_service.get_unread_count.assert_called_once_with(10)
        assert result == 5

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        mock_service.create.return_value = {
            "id": 1,
            "user_id": 10,
            "title": "Test",
            "message": "Msg",
            "type": "info",
            "read": False,
        }

        data = NotificationCreate(
            user_id=10,
            title="Test",
            message="Msg",
            type=NotificationType.INFO,
        )

        result = await controller.create(data, actor_id=5)

        mock_service.create.assert_called_once_with(data, 5)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_mark_as_read_delegates_to_service(self, controller, mock_service):
        """Test mark_as_read delegates to service."""

        mock_service.mark_as_read.return_value = 3

        result = await controller.mark_as_read([1, 2, 3], user_id=10)

        mock_service.mark_as_read.assert_called_once_with([1, 2, 3], 10)
        assert result == 3

    @pytest.mark.asyncio
    async def test_mark_all_as_read_delegates_to_service(
        self, controller, mock_service
    ):
        """Test mark_all_as_read delegates to service."""

        mock_service.mark_all_as_read.return_value = 7

        result = await controller.mark_all_as_read(user_id=10)

        mock_service.mark_all_as_read.assert_called_once_with(10)
        assert result == 7
