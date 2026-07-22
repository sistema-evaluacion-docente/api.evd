"""Tests for SettingsRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.repositories.base import BaseRepository
from api.repositories.settings import SettingsRepository
from api.schemas.setting import SettingFilters


class TestSettingsRepository:
    """Test suite for SettingsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return SettingsRepository(mock_db)

    @pytest.fixture
    def mock_setting_model(self):
        """Mock SettingModel instance."""

        setting = MagicMock(spec=SettingModel)
        setting.id = 1
        setting.key = "app_name"
        setting.value = "My App"
        setting.value_type = "STRING"
        setting.description = "Application name"
        setting.changed_by = None
        return setting

    @pytest.fixture
    def mock_history_model(self):
        """Mock SettingHistoryModel instance."""

        history = MagicMock(spec=SettingHistoryModel)
        history.id = 1
        history.key = "app_name"
        history.old_value = "Old Value"
        history.new_value = "New Value"
        history.changed_by = "user-uid"
        history.change_reason = "Test update"
        return history

    def test_inherits_base_repository(self, repo):
        """Test SettingsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_key_found(self, repo, mock_db, mock_setting_model):
        """Test get_by_key returns setting when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_setting_model
        )

        result = repo.get_by_key("app_name")

        assert result == mock_setting_model

    def test_get_by_key_not_found(self, repo, mock_db):
        """Test get_by_key returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_key("nonexistent")

        assert result is None

    def test_search_no_filters(self, repo, mock_db, mock_setting_model):
        """Test search with no filters returns all settings paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_setting_model
        ]

        filters = SettingFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_setting_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_setting_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_setting_model
        ]

        filters = SettingFilters(search="app")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_value_type_filter(self, repo, mock_db, mock_setting_model):
        """Test search applies equality filter for value_type."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_setting_model
        ]

        filters = SettingFilters(value_type="STRING")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_setting_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_setting_model
        ]

        filters = SettingFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_create_setting(self, repo, mock_db, mock_setting_model):
        """Test create_setting creates and returns setting."""

        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()

        result = repo.create_setting(
            {"key": "app_name", "value": "My App", "value_type": "STRING"}
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_update_setting(self, repo, mock_db, mock_setting_model):
        """Test update_setting updates attributes."""

        result = repo.update_setting(mock_setting_model, {"value": "New Value"})

        assert mock_setting_model.value == "New Value"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_setting_model)
        assert result == mock_setting_model

    def test_delete_setting_success(self, repo, mock_db, mock_setting_model):
        """Test delete_setting deletes and returns setting."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_setting_model
        )

        result = repo.delete_setting(1)

        assert result == mock_setting_model
        mock_db.delete.assert_called_once_with(mock_setting_model)
        mock_db.commit.assert_called_once()

    def test_delete_setting_not_found(self, repo, mock_db):
        """Test delete_setting returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.delete_setting(999)

        assert result is None

    def test_add_history(self, repo, mock_db, mock_history_model):
        """Test add_history creates history entry."""

        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()

        result = repo.add_history(
            {
                "key": "app_name",
                "old_value": "Old",
                "new_value": "New",
                "changed_by": "user-uid",
                "change_reason": "Test",
            }
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_get_history_with_key_filter(self, repo, mock_db, mock_history_model):
        """Test get_history filters by key."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_history_model
        ]

        pagination = PaginationParams(page=1, limit=10)
        items, total = repo.get_history(key="app_name", pagination=pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_get_history_without_pagination(self, repo, mock_db, mock_history_model):
        """Test get_history returns all items without pagination."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history_model]

        items, total = repo.get_history(key="app_name")

        assert total == 1
        assert items == [mock_history_model]
