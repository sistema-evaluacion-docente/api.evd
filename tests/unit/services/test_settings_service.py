"""Tests for SettingService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, SettingAlreadyExistsError
from api.models.setting import SettingModel
from api.schemas.setting import SettingCreate, SettingFilters, SettingUpdate
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
        setting.department_id = None
        setting.department = None
        setting.changed_by = None
        setting.effective_from = "2024-01-01T00:00:00Z"
        setting.created_at = "2024-01-01T00:00:00Z"
        setting.updated_at = "2024-01-01T00:00:00Z"
        return setting

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "uid": "test-uid-123", "roles": ["ADMIN"]}

    @pytest.fixture
    def director_user(self):
        """Director of department 7."""

        return {
            "id": 50,
            "uid": "director-uid",
            "roles": ["DIRECTOR DE DEPARTAMENTO"],
            "department_id": 7,
        }

    @pytest.fixture
    def department_setting(self, mock_setting):
        """A setting owned by department 7."""

        department = MagicMock()
        department.name = "Ingeniería de Sistemas"

        mock_setting.department_id = 7
        mock_setting.department = department

        return mock_setting

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
    async def test_get_all_includes_changed_by_user_info(
        self, service, mock_settings_repo, mock_setting
    ):
        """Test get_all includes changed-by user name and avatar URL."""

        mock_user = MagicMock()
        mock_user.name = "Admin User"
        mock_user.avatar_url = "http://avatar.example.com/admin.png"
        mock_setting.changed_by_user = mock_user

        mock_settings_repo.search.return_value = ([mock_setting], 1)

        filters = SettingFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        item = result["items"][0]
        assert item["changed_by_name"] == "Admin User"
        assert item["changed_by_avatar_url"] == "http://avatar.example.com/admin.png"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_settings_repo, mock_setting):
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
    async def test_get_by_key_found(self, service, mock_settings_repo, mock_setting):
        """Test get_by_key returns setting dict when found."""

        mock_settings_repo.resolve.return_value = mock_setting

        result = await service.get_by_key("app_name")

        assert result is not None
        assert result["key"] == "app_name"

    @pytest.mark.asyncio
    async def test_get_by_key_not_found(self, service, mock_settings_repo):
        """Test get_by_key returns None when not found."""

        mock_settings_repo.resolve.return_value = None

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

        with pytest.raises(SettingAlreadyExistsError):
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
    async def test_get_history_with_pagination(self, service, mock_settings_repo):
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

    @pytest.mark.asyncio
    async def test_get_history_includes_changed_by_user_info(
        self, service, mock_settings_repo
    ):
        """Test get_history includes changed-by user name and avatar URL."""

        mock_history = MagicMock()
        mock_history.id = 1
        mock_history.key = "app_name"
        mock_history.old_value = "Old"
        mock_history.new_value = "New"
        mock_history.changed_by = "user-uid"
        mock_history.change_reason = "Test"
        mock_history.changed_at = "2024-01-01T00:00:00Z"

        mock_user = MagicMock()
        mock_user.name = "Admin User"
        mock_user.avatar_url = "http://avatar.example.com/admin.png"
        mock_history.changed_by_user = mock_user

        mock_settings_repo.get_history.return_value = ([mock_history], 1)

        pagination = PaginationParams(page=1, limit=10)
        result = await service.get_history(key="app_name", pagination=pagination)

        item = result["items"][0]
        assert item["changed_by_name"] == "Admin User"
        assert item["changed_by_avatar_url"] == "http://avatar.example.com/admin.png"

    # ------------------------------------------------------------------ #
    # Department scoping
    # ------------------------------------------------------------------ #
    @pytest.mark.asyncio
    async def test_get_all_pins_a_director_to_its_own_department(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test get_all overrides the department a director asked for."""

        mock_settings_repo.search.return_value = ([mock_setting], 1)

        filters = SettingFilters(department_id=99)
        pagination = PaginationParams(page=1, limit=10)

        await service.get_all(filters, pagination, director_user)

        applied_filters = mock_settings_repo.search.call_args.args[0]
        assert applied_filters.department_id == 7

    @pytest.mark.asyncio
    async def test_get_all_keeps_the_department_an_admin_asked_for(
        self, service, mock_settings_repo, mock_setting, current_user
    ):
        """Test get_all lets an ADMIN list any department."""

        mock_settings_repo.search.return_value = ([mock_setting], 1)

        filters = SettingFilters(department_id=99)
        pagination = PaginationParams(page=1, limit=10)

        await service.get_all(filters, pagination, current_user)

        applied_filters = mock_settings_repo.search.call_args.args[0]
        assert applied_filters.department_id == 99

    @pytest.mark.asyncio
    async def test_get_all_for_a_director_without_department_raises(
        self, service, mock_settings_repo
    ):
        """Test get_all refuses a director with no department assigned."""

        director = {"id": 50, "uid": "x", "roles": ["DIRECTOR DE DEPARTAMENTO"]}

        with pytest.raises(PermissionDeniedError):
            await service.get_all(
                SettingFilters(), PaginationParams(page=1, limit=10), director
            )

        mock_settings_repo.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_key_resolves_against_the_director_department(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test get_by_key resolves the value in effect for the director."""

        mock_settings_repo.resolve.return_value = department_setting

        result = await service.get_by_key("app_name", director_user)

        mock_settings_repo.resolve.assert_called_once_with("app_name", 7)
        assert result["department_id"] == 7
        assert result["scope"] == "DEPARTMENT"

    @pytest.mark.asyncio
    async def test_get_by_id_of_another_department_raises_for_a_director(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test a director cannot read another department's setting."""

        mock_setting.department_id = 42

        mock_settings_repo.get.return_value = mock_setting

        with pytest.raises(PermissionDeniedError):
            await service.get_by_id(1, director_user)

    @pytest.mark.asyncio
    async def test_get_by_id_of_a_global_setting_is_allowed_for_a_director(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test a director reads the institutional settings it inherits."""

        mock_settings_repo.get.return_value = mock_setting

        result = await service.get_by_id(1, director_user)

        assert result["scope"] == "GLOBAL"

    @pytest.mark.asyncio
    async def test_create_by_a_director_is_forced_into_its_own_department(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test a director's setting lands on its own department."""

        mock_settings_repo.get_by_key.return_value = None
        mock_settings_repo.create_setting.return_value = department_setting

        data = SettingCreate(key="app_name", value="My App")

        result = await service.create(data, director_user)

        payload = mock_settings_repo.create_setting.call_args.args[0]
        assert payload["department_id"] == 7
        assert result["department_id"] == 7

    @pytest.mark.asyncio
    async def test_create_by_a_director_for_another_department_raises(
        self, service, mock_settings_repo, director_user
    ):
        """Test a director cannot create a setting for another department."""

        data = SettingCreate(key="app_name", value="My App", department_id=42)

        with pytest.raises(PermissionDeniedError):
            await service.create(data, director_user)

        mock_settings_repo.create_setting.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_by_an_admin_keeps_the_requested_department(
        self, service, mock_settings_repo, department_setting, current_user
    ):
        """Test an ADMIN creates a setting for any department."""

        mock_settings_repo.get_by_key.return_value = None
        mock_settings_repo.create_setting.return_value = department_setting

        data = SettingCreate(key="app_name", value="My App", department_id=7)

        await service.create(data, current_user)

        payload = mock_settings_repo.create_setting.call_args.args[0]
        assert payload["department_id"] == 7

    @pytest.mark.asyncio
    async def test_create_checks_duplicates_within_the_same_scope_only(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test a department may reuse a key the institution already defines."""

        mock_settings_repo.get_by_key.return_value = None
        mock_settings_repo.create_setting.return_value = department_setting

        data = SettingCreate(key="app_name", value="My App")

        await service.create(data, director_user)

        mock_settings_repo.get_by_key.assert_called_once_with("app_name", 7)

    @pytest.mark.asyncio
    async def test_create_duplicate_key_in_the_same_department_raises(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test a department cannot define the same key twice."""

        mock_settings_repo.get_by_key.return_value = department_setting

        data = SettingCreate(key="app_name", value="My App")

        with pytest.raises(SettingAlreadyExistsError):
            await service.create(data, director_user)

    @pytest.mark.asyncio
    async def test_update_of_a_global_setting_raises_for_a_director(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test a director cannot change an institutional value."""

        mock_settings_repo.get.return_value = mock_setting

        data = SettingUpdate(value="New Value")

        with pytest.raises(PermissionDeniedError):
            await service.update(1, data, director_user)

        mock_settings_repo.update_setting.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_of_another_department_setting_raises_for_a_director(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test a director cannot change another department's value."""

        mock_setting.department_id = 42
        mock_settings_repo.get.return_value = mock_setting

        data = SettingUpdate(value="New Value")

        with pytest.raises(PermissionDeniedError):
            await service.update(1, data, director_user)

    @pytest.mark.asyncio
    async def test_update_of_its_own_department_setting_records_the_scope(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test the history entry keeps the department the change belongs to."""

        mock_settings_repo.get.return_value = department_setting
        mock_settings_repo.update_setting.return_value = department_setting

        data = SettingUpdate(value="New Value", change_reason="Ajuste del departamento")

        result = await service.update(1, data, director_user)

        assert result is not None
        history = mock_settings_repo.add_history.call_args.args[0]
        assert history["department_id"] == 7

    @pytest.mark.asyncio
    async def test_delete_of_a_global_setting_raises_for_a_director(
        self, service, mock_settings_repo, mock_setting, director_user
    ):
        """Test a director cannot delete an institutional setting."""

        mock_settings_repo.get.return_value = mock_setting

        with pytest.raises(PermissionDeniedError):
            await service.delete(1, director_user)

        mock_settings_repo.delete_setting.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_of_its_own_department_setting_succeeds(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """Test a director deletes its own department's override."""

        mock_settings_repo.get.return_value = department_setting
        mock_settings_repo.delete_setting.return_value = department_setting

        result = await service.delete(1, director_user)

        assert result is not None
        mock_settings_repo.delete_setting.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_history_forwards_the_department_scope(
        self, service, mock_settings_repo
    ):
        """Test get_history asks the repository for one scope only."""

        mock_settings_repo.get_history.return_value = ([], 0)

        pagination = PaginationParams(page=1, limit=10)
        await service.get_history("app_name", pagination, department_id=7)

        mock_settings_repo.get_history.assert_called_once_with(
            "app_name", pagination, 7
        )

    @pytest.mark.asyncio
    async def test_duplicate_error_names_the_department_it_collided_with(
        self, service, mock_settings_repo, department_setting, director_user
    ):
        """The 409 has to say which scope already holds the key."""

        mock_settings_repo.get_by_key.return_value = department_setting

        with pytest.raises(SettingAlreadyExistsError) as exc:
            await service.create(
                SettingCreate(key="app_name", value="My App"), director_user
            )

        assert "Ingeniería de Sistemas" in exc.value.message

    @pytest.mark.asyncio
    async def test_duplicate_error_names_the_institutional_scope(
        self, service, mock_settings_repo, mock_setting, current_user
    ):
        """A collision with the institutional row says so."""

        mock_settings_repo.get_by_key.return_value = mock_setting

        with pytest.raises(SettingAlreadyExistsError) as exc:
            await service.create(
                SettingCreate(key="app_name", value="My App"), current_user
            )

        assert "institucional" in exc.value.message
