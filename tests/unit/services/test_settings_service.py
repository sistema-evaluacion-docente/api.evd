"""Tests for SettingService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError
from api.models.setting import SettingModel
from api.schemas.setting import (
    SettingCreate,
    SettingFilters,
    SettingUpdate,
)
from api.services.settings_service import SettingService


class TestSettingService:
    """Test suite for SettingService."""

    @pytest.fixture
    def mock_settings_repo(self):
        """Mock SettingsRepository."""

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
    def service(self, mock_settings_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return SettingService(
            mock_settings_repo,
            mock_audit_service,
        )

    @pytest.fixture
    def mock_setting(self):
        """Mock SettingModel instance."""

        setting = MagicMock(spec=SettingModel)
        setting.id = 1
        setting.key = "app_name"
        setting.value = "My App"
        setting.value_type = "STRING"
        setting.description = "Application name"
        setting.changed_by = None
        setting.effective_from = "2024-01-01T00:00:00Z"
        setting.created_at = "2024-01-01T00:00:00Z"
        setting.updated_at = "2024-01-01T00:00:00Z"
        return setting

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "uid": "test-uid-123", "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_settings(
        self, service, mock_settings_repo, mock_setting
    ):
        """Test get_all returns paginated settings."""

        mock_settings_repo.search.return_value = ([mock_setting], 1)

        filters = SettingFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, service, mock_settings_repo, mock_setting
    ):
        """Test get_by_id returns setting dict when found."""

        mock_settings_repo.get.return_value = mock_setting

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["key"] == "app_name"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_settings_repo):
        """Test get_by_id returns None when not found."""

        mock_settings_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_key_found(
        self, service, mock_settings_repo, mock_setting
    ):
        """Test get_by_key returns setting dict when found."""

        mock_settings_repo.get_by_key.return_value = mock_setting

        result = await service.get_by_key("app_name")

        assert result is not None
        assert result["key"] == "app_name"

    @pytest.mark.asyncio
    async def test_get_by_key_not_found(self, service, mock_settings_repo):
        """Test get_by_key returns None when not found."""

        mock_settings_repo.get_by_key.return_value = None

        result = await service.get_by_key("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_setting_success(
        self,
        service,
        mock_settings_repo,
        mock_audit_service,
        mock_setting,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_settings_repo.get_by_key.return_value = None
        mock_settings_repo.create_setting.return_value = mock_setting

        data = SettingCreate(
            key="app_name", value="My App", value_type="STRING", description="App name"
        )

        result = await service.create(data, current_user)

        assert result is not None
        mock_settings_repo.create_setting.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_setting_duplicate_key_raises(
        self, service, mock_settings_repo, mock_setting
    ):
        """Test create raises when key already exists."""

        mock_settings_repo.get_by_key.return_value = mock_setting

        data = SettingCreate(key="app_name", value="My App")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_setting_success(
        self,
        service,
        mock_settings_repo,
        mock_audit_service,
        mock_setting,
        current_user,
    ):
        """Test update succeeds when setting exists."""

        mock_settings_repo.get.return_value = mock_setting
        mock_settings_repo.update_setting.return_value = mock_setting
        mock_settings_repo.add_history.return_value = MagicMock()

        data = SettingUpdate(value="New Value", change_reason="Test update")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_settings_repo.update_setting.assert_called_once()
        mock_settings_repo.add_history.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_setting_not_found(
        self, service, mock_settings_repo, current_user
    ):
        """Test update returns None when setting not found."""

        mock_settings_repo.get.return_value = None

        data = SettingUpdate(value="New Value")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_setting_success(
        self,
        service,
        mock_settings_repo,
        mock_audit_service,
        mock_setting,
        current_user,
    ):
        """Test delete succeeds when setting exists."""

        mock_settings_repo.get.return_value = mock_setting
        mock_settings_repo.delete_setting.return_value = mock_setting

        result = await service.delete(1, current_user)

        assert result is not None
        mock_settings_repo.delete_setting.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_setting_not_found(
        self, service, mock_settings_repo, current_user
    ):
        """Test delete returns None when setting not found."""

        mock_settings_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_history_with_pagination(
        self, service, mock_settings_repo
    ):
        """Test get_history returns paginated history."""

        mock_history = MagicMock()
        mock_history.id = 1
        mock_history.key = "app_name"
        mock_history.old_value = "Old"
        mock_history.new_value = "New"
        mock_history.changed_by = "user-uid"
        mock_history.change_reason = "Test"
        mock_history.changed_at = "2024-01-01T00:00:00Z"

        mock_settings_repo.get_history.return_value = ([mock_history], 1)

        pagination = PaginationParams(page=1, limit=10)
        result = await service.get_history(key="app_name", pagination=pagination)

        assert result["total"] == 1
        assert len(result["items"]) == 1
