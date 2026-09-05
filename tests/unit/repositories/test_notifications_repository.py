"""Tests for NotificationsRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.notification import NotificationModel
from api.repositories.base import BaseRepository
from api.repositories.notifications import NotificationsRepository
from api.schemas.notification import NotificationFilters


class TestNotificationsRepository:
    """Test suite for NotificationsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return NotificationsRepository(mock_db)

    @pytest.fixture
    def mock_notification(self):
        """Mock NotificationModel instance."""

        row = MagicMock(spec=NotificationModel)
        row.id = 1
        row.user_id = 3
        row.read = False
        return row

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock a chained SQLAlchemy query."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        return query

    def test_inherits_base_repository(self, repo):
        """Test NotificationsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_user_no_filters(self, repo, mock_query, mock_notification):
        """Test get_by_user with no filters just scopes by user and paginates."""

        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_notification]
        filters = NotificationFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.get_by_user(3, filters, pagination)

        assert total == 1
        assert items == [mock_notification]

    def test_get_by_user_with_type_and_read_filters(
        self, repo, mock_query, mock_notification
    ):
        """Test get_by_user applies the type and read filters."""

        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_notification]
        filters = NotificationFilters(type="info", read=True)
        pagination = PaginationParams(page=1, limit=10)

        repo.get_by_user(3, filters, pagination)

        assert mock_query.filter.call_count >= 3

    def test_get_by_user_with_search_filter(
        self, repo, mock_query, mock_notification
    ):
        """Test get_by_user applies the title/message search filter."""

        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_notification]
        filters = NotificationFilters(search="plan")
        pagination = PaginationParams(page=1, limit=10)

        repo.get_by_user(3, filters, pagination)

        mock_query.filter.assert_called()

    def test_get_unread_count(self, repo, mock_query):
        """Test get_unread_count filters by user and unread state."""

        mock_query.count.return_value = 4

        result = repo.get_unread_count(3)

        assert result == 4

    def test_mark_as_read_with_no_ids_short_circuits(self, repo, mock_db):
        """Test mark_as_read returns 0 without touching the database."""

        result = repo.mark_as_read([], 3)

        assert result == 0
        mock_db.query.assert_not_called()

    def test_mark_as_read_updates_the_given_notifications(
        self, repo, mock_query, mock_db
    ):
        """Test mark_as_read updates the matching rows and commits."""

        mock_query.update.return_value = 2

        result = repo.mark_as_read([1, 2], 3)

        assert result == 2
        mock_db.commit.assert_called_once()

    def test_mark_all_as_read(self, repo, mock_query, mock_db):
        """Test mark_all_as_read updates every unread row for the user."""

        mock_query.update.return_value = 5

        result = repo.mark_all_as_read(3)

        assert result == 5
        mock_db.commit.assert_called_once()
