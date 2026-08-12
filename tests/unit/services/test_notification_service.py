"""
Tests for NotificationService layer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.core.pagination import PaginationParams
from api.schemas.notification import (
    NotificationCreate,
    NotificationFilters,
    NotificationType,
)
from api.services.notification_service import NotificationService


class TestNotificationService:
    """Test suite for NotificationService."""

    @pytest.fixture
    def mock_notifications_repo(self):
        """Mock NotificationsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_notifications_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return NotificationService(mock_notifications_repo, mock_audit_service)

    def _make_mock_notification(self, **overrides):
        """Helper to build a mock notification model."""

        defaults = {
            "id": 1,
            "user_id": 10,
            "title": "Test notification",
            "message": "Test message",
            "type": "info",
            "read": False,
            "link": None,
        }
        defaults.update(overrides)
        n = MagicMock()
        for k, v in defaults.items():
            setattr(n, k, v)
        return n

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_notifications(
        self, service, mock_notifications_repo
    ):
        """Test get_all returns paginated notifications for a user."""

        items = [self._make_mock_notification(id=1), self._make_mock_notification(id=2)]
        mock_notifications_repo.get_by_user.return_value = (items, 2)

        filters = NotificationFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(
            user_id=10, filters=filters, pagination=pagination
        )

        assert result["items"][0]["id"] == 1
        assert result["items"][1]["id"] == 2
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        mock_notifications_repo.get_by_user.assert_called_once_with(
            10, filters, pagination
        )

    @pytest.mark.asyncio
    async def test_get_unread_count_returns_count(
        self, service, mock_notifications_repo
    ):
        """Test get_unread_count returns the unread count."""

        mock_notifications_repo.get_unread_count.return_value = 5

        result = await service.get_unread_count(user_id=10)

        assert result == 5
        mock_notifications_repo.get_unread_count.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_create_saves_notification_and_broadcasts(
        self, service, mock_notifications_repo
    ):
        """Test create saves notification to DB and broadcasts via WebSocket."""

        mock_notification = self._make_mock_notification()
        mock_notifications_repo.create.return_value = mock_notification

        data = NotificationCreate(
            user_id=10,
            title="Test notification",
            message="Test message",
            type=NotificationType.INFO,
        )

        with patch.object(
            service, "_broadcast_notification", new_callable=AsyncMock
        ) as mock_broadcast:
            result = await service.create(data, actor_id=1)

        assert result["id"] == 1
        assert result["user_id"] == 10
        assert result["title"] == "Test notification"
        mock_notifications_repo.create.assert_called_once()
        mock_notifications_repo.db.commit.assert_called_once()
        mock_notifications_repo.db.refresh.assert_called_once_with(mock_notification)
        mock_broadcast.assert_called_once_with(mock_notification)

    @pytest.mark.asyncio
    async def test_create_logs_audit_when_actor_provided(
        self, service, mock_notifications_repo, mock_audit_service
    ):
        """Test create logs an audit entry when actor_id is provided."""

        mock_notification = self._make_mock_notification()
        mock_notifications_repo.create.return_value = mock_notification

        data = NotificationCreate(
            user_id=10,
            title="Test",
            message="Msg",
            type=NotificationType.INFO,
        )

        with patch.object(service, "_broadcast_notification", new_callable=AsyncMock):
            await service.create(data, actor_id=5)

        mock_audit_service.log.assert_called_once()
        call_kwargs = mock_audit_service.log.call_args[1]
        assert call_kwargs["action"] == "CREATE"
        assert call_kwargs["entity_name"] == "notifications"
        assert call_kwargs["actor_id"] == 5

    @pytest.mark.asyncio
    async def test_create_skips_audit_when_no_actor(
        self, service, mock_notifications_repo, mock_audit_service
    ):
        """Test create does not log audit when actor_id is None."""

        mock_notification = self._make_mock_notification()
        mock_notifications_repo.create.return_value = mock_notification

        data = NotificationCreate(
            user_id=10,
            title="Test",
            message="Msg",
            type=NotificationType.INFO,
        )

        with patch.object(service, "_broadcast_notification", new_callable=AsyncMock):
            await service.create(data, actor_id=None)

        mock_audit_service.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_as_read_delegates_to_repository(
        self, service, mock_notifications_repo
    ):
        """Test mark_as_read delegates to repository."""

        mock_notifications_repo.mark_as_read.return_value = 3

        result = await service.mark_as_read([1, 2, 3], user_id=10)

        assert result == 3
        mock_notifications_repo.mark_as_read.assert_called_once_with([1, 2, 3], 10)

    @pytest.mark.asyncio
    async def test_mark_all_as_read_delegates_to_repository(
        self, service, mock_notifications_repo
    ):
        """Test mark_all_as_read delegates to repository."""

        mock_notifications_repo.mark_all_as_read.return_value = 7

        result = await service.mark_all_as_read(user_id=10)

        assert result == 7
        mock_notifications_repo.mark_all_as_read.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_broadcast_notification_sends_to_correct_channel(self, service):
        """Test _broadcast_notification sends event to the user's channel."""

        mock_notification = self._make_mock_notification(id=42, user_id=10)

        with patch(
            "api.services.notification_service.connection_manager"
        ) as mock_manager:
            mock_manager.broadcast = AsyncMock()

            await service._broadcast_notification(mock_notification)

            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            assert call_args[0][0] == "notifications:10"
            event = call_args[0][1]
            assert event.notification_id == 42
            assert event.user_id == 10
            assert event.title == "Test notification"
