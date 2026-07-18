"""
Tests for UsersController layer.
"""

from unittest.mock import MagicMock, AsyncMock
import pytest

from api.controllers.users import UsersController
from api.core.pagination import PaginationParams
from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserFilters,
    UserRolesUpdate,
    UserStatusUpdate,
    RoleName,
)


class TestUsersController:
    """Test suite for UsersController."""

    @pytest.fixture
    def mock_service(self):
        """Mock UserService."""

        service = MagicMock()
        service.login = AsyncMock()
        service.get_by_uid = AsyncMock()
        service.get_all = AsyncMock()
        service.create_user = AsyncMock()
        service.update_user = AsyncMock()
        service.replace_roles = AsyncMock()
        service.update_status = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return UsersController(mock_service)

    @pytest.mark.asyncio
    async def test_login_success(self, controller, mock_service):
        """Test login delegates to service."""

        current_user = MagicMock()
        mock_service.login.return_value = {"uid": "test-uid", "name": "Test"}

        result = await controller.login(current_user)

        mock_service.login.assert_called_once_with(current_user)
        assert result == {"uid": "test-uid", "name": "Test"}

    @pytest.mark.asyncio
    async def test_login_returns_none(self, controller, mock_service):
        """Test login returns None when service returns None."""

        current_user = MagicMock()
        mock_service.login.return_value = None

        result = await controller.login(current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_uid_success(self, controller, mock_service):
        """Test get_by_uid delegates to service."""

        mock_service.get_by_uid.return_value = {"uid": "test-uid", "name": "Test"}

        result = await controller.get_by_uid("test-uid")

        mock_service.get_by_uid.assert_called_once_with("test-uid")
        assert result == {"uid": "test-uid", "name": "Test"}

    @pytest.mark.asyncio
    async def test_get_by_uid_not_found(self, controller, mock_service):
        """Test get_by_uid returns None when not found."""

        mock_service.get_by_uid.return_value = None

        result = await controller.get_by_uid("nonexistent-uid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_success(self, controller, mock_service):
        """Test get_all delegates to service."""

        mock_service.get_all.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = UserFilters(search="test")
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_create_user_success(self, controller, mock_service):
        """Test create_user delegates to service."""

        current_user = MagicMock()
        data = UserCreate(
            email="test@example.com",
            username="testuser",
            name="Test User",
            roles=[RoleName.DOCENTE],
        )
        mock_service.create_user.return_value = {
            "uid": "new-uid",
            "email": "test@example.com",
        }

        result = await controller.create_user(data, current_user)

        mock_service.create_user.assert_called_once_with(data, current_user)
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_update_success(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = MagicMock()
        current_user.uid = "test-uid"
        data = UserUpdate(name="Updated Name")

        mock_service.update_user.return_value = {
            "uid": "test-uid",
            "name": "Updated Name",
        }

        result = await controller.update(data, current_user)

        mock_service.update_user.assert_called_once_with("test-uid", data)
        assert result["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_replace_roles_success(self, controller, mock_service):
        """Test replace_roles delegates to service."""

        current_user = MagicMock()
        payload = UserRolesUpdate(roles=[RoleName.ADMIN])
        mock_service.replace_roles.return_value = {
            "uid": "test-uid",
            "roles": ["ADMIN"],
        }

        result = await controller.replace_roles("test-uid", payload, current_user)

        mock_service.replace_roles.assert_called_once_with(
            "test-uid", payload, current_user
        )
        assert "ADMIN" in result["roles"]

    @pytest.mark.asyncio
    async def test_update_status_success(self, controller, mock_service):
        """Test update_status delegates to service."""

        payload = UserStatusUpdate(active=False)
        mock_service.update_status.return_value = {"uid": "test-uid", "active": False}

        result = await controller.update_status("test-uid", payload)

        mock_service.update_status.assert_called_once_with("test-uid", payload)
        assert result["active"] is False
