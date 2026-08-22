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

    @staticmethod
    def _stub_by_key(mock_db, result):
        """Wire the query chain `get_by_key` walks to end in ``result``."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = result

        return mock_query

    def test_get_by_key_found(self, repo, mock_db, mock_setting_model):
        """Test get_by_key returns setting when found."""

        self._stub_by_key(mock_db, mock_setting_model)

        result = repo.get_by_key("app_name")

        assert result == mock_setting_model

    def test_get_by_key_not_found(self, repo, mock_db):
        """Test get_by_key returns None when not found."""

        self._stub_by_key(mock_db, None)

        result = repo.get_by_key("nonexistent")

        assert result is None

    def test_get_by_key_without_department_filters_by_key_and_global_scope(
        self, repo, mock_db, mock_setting_model
    ):
        """Test get_by_key narrows to the institutional row by default."""

        mock_query = self._stub_by_key(mock_db, mock_setting_model)

        repo.get_by_key("app_name")

        # One filter for the key, one pinning the scope.
        assert mock_query.filter.call_count == 2

    def test_get_by_key_with_department_filters_by_that_department(
        self, repo, mock_db, mock_setting_model
    ):
        """Test get_by_key narrows to a department's own row."""

        mock_query = self._stub_by_key(mock_db, mock_setting_model)

        result = repo.get_by_key("app_name", department_id=7)

        assert result == mock_setting_model
        assert mock_query.filter.call_count == 2

    def test_resolve_without_department_returns_global_setting(
        self, repo, mock_db, mock_setting_model
    ):
        """Test resolve falls back to the institutional value."""

        self._stub_by_key(mock_db, mock_setting_model)

        result = repo.resolve("app_name")

        assert result == mock_setting_model

    def test_resolve_prefers_department_setting_over_global(self, repo):
        """Test resolve returns the department override when it exists."""

        department_setting = MagicMock(spec=SettingModel)
        repo.get_by_key = MagicMock(return_value=department_setting)

        result = repo.resolve("app_name", department_id=7)

        assert result == department_setting
        repo.get_by_key.assert_called_once_with("app_name", 7)

    def test_resolve_falls_back_to_global_when_department_has_no_override(self, repo):
        """Test resolve reads the institutional value for a department without one."""

        global_setting = MagicMock(spec=SettingModel)
        repo.get_by_key = MagicMock(side_effect=[None, global_setting])

        result = repo.resolve("app_name", department_id=7)

        assert result == global_setting
        assert repo.get_by_key.call_args_list[0].args == ("app_name", 7)
        assert repo.get_by_key.call_args_list[1].args == ("app_name",)

    @staticmethod
    def _stub_search(mock_db, mock_setting_model, total=1):
        """Stub the query chain of search and hand the query mock back."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = total
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_setting_model
        ]

        return mock_query

    @staticmethod
    def _scope_clause(mock_query) -> str:
        """The SQL of the first filter, which is always the scope."""

        return str(mock_query.filter.call_args_list[0].args[0])

    def test_search_without_department_returns_only_global_settings(
        self, repo, mock_db, mock_setting_model
    ):
        """Test search with no department covers the institutional scope only."""

        mock_query = self._stub_search(mock_db, mock_setting_model)

        filters = SettingFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_setting_model]
        assert self._scope_clause(mock_query) == "settings.department_id IS NULL"
        mock_query.outerjoin.assert_called_once()
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_setting_model):
        """Test search applies ilike filter for search term, on top of the scope."""

        mock_query = self._stub_search(mock_db, mock_setting_model)

        filters = SettingFilters(search="app")
        pagination = PaginationParams(page=1, limit=10)

        _items, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.call_count == 2
        assert "LIKE" in str(mock_query.filter.call_args_list[1].args[0])

    def test_search_with_department_includes_global_settings(
        self, repo, mock_db, mock_setting_model
    ):
        """Test search of a department also brings the institutional settings."""

        mock_query = self._stub_search(mock_db, mock_setting_model, total=2)

        filters = SettingFilters(department_id=7)
        pagination = PaginationParams(page=1, limit=10)

        _items, total = repo.search(filters, pagination)

        assert total == 2
        clause = self._scope_clause(mock_query)
        assert "settings.department_id = " in clause
        assert "OR settings.department_id IS NULL" in clause

    def test_search_excluding_global_keeps_only_department_settings(
        self, repo, mock_db, mock_setting_model
    ):
        """Test search can drop the institutional settings from the list."""

        mock_query = self._stub_search(mock_db, mock_setting_model)

        filters = SettingFilters(department_id=7, include_global=False)
        pagination = PaginationParams(page=1, limit=10)

        _items, total = repo.search(filters, pagination)

        assert total == 1
        clause = self._scope_clause(mock_query)
        assert "settings.department_id = " in clause
        assert "IS NULL" not in clause

    def test_search_with_value_type_filter(self, repo, mock_db, mock_setting_model):
        """Test search applies equality filter for value_type."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value.options.return_value = mock_query
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
        mock_query.outerjoin.return_value.options.return_value = mock_query
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

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_setting_model
        )

        result = repo.delete_setting(1)

        assert result == mock_setting_model
        mock_db.delete.assert_called_once_with(mock_setting_model)
        mock_db.commit.assert_called_once()

    def test_delete_setting_not_found(self, repo, mock_db):
        """Test delete_setting returns None when not found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None
        )

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
        mock_query.outerjoin.return_value.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_history_model
        ]

        pagination = PaginationParams(page=1, limit=10)
        items, total = repo.get_history(key="app_name", pagination=pagination)

        assert total == 1
        # One filter for the key, one pinning the scope.
        assert mock_query.filter.call_count == 2

    def test_get_history_scoped_to_a_department(
        self, repo, mock_db, mock_history_model
    ):
        """Test get_history returns the entries of one department only."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history_model]

        items, total = repo.get_history(key="app_name", department_id=7)

        assert total == 1
        assert items == [mock_history_model]
        assert mock_query.filter.call_count == 2

    def test_get_history_without_pagination(self, repo, mock_db, mock_history_model):
        """Test get_history returns all items without pagination."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history_model]

        items, total = repo.get_history(key="app_name")

        assert total == 1
        assert items == [mock_history_model]
