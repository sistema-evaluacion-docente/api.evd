"""
Tests for UserService layer.
"""

from unittest.mock import MagicMock, AsyncMock
import pytest

from api.core.pagination import PaginationParams
from api.services.user_service import UserService
from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserFilters,
    UserRolesUpdate,
    UserStatusUpdate,
    RoleName,
)
from api.exceptions import (
    PermissionDeniedError,
    InvalidRoleError,
    UserNotFoundError,
)


class TestUserService:
    """Test suite for UserService."""

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_users_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return UserService(mock_users_repo, mock_audit_service)

    @pytest.fixture
    def mock_user(self):
        """Mock user model."""
        from api.models.user import UserModel

        user = MagicMock(spec=UserModel)
        user.id = 1
        user.uid = "test-uid-123"
        user.email = "test@example.com"
        user.name = "Test User"
        user.active = True
        user.avatar_url = None
        user.teacher = None
        return user

    @pytest.mark.asyncio
    async def test_login_success(self, service, mock_users_repo, mock_user):
        """Test login returns user data when user exists."""

        mock_users_repo.get_by_email.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        current_user = MagicMock()
        current_user.email = "test@example.com"
        current_user.uid = "test-uid-123"

        result = await service.login(current_user)

        assert result is not None
        assert result["uid"] == "test-uid-123"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, service, mock_users_repo):
        """Test login returns None when user not found."""

        mock_users_repo.get_by_email.return_value = None

        current_user = MagicMock()
        current_user.email = "nonexistent@example.com"

        result = await service.login(current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_login_current_user_none(self, service):
        """Test login returns None when current_user is None."""

        result = await service.login(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_uid_found(self, service, mock_users_repo, mock_user):
        """Test get_by_uid returns user data when found."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        result = await service.get_by_uid("test-uid-123")

        assert result is not None
        assert result["uid"] == "test-uid-123"

    @pytest.mark.asyncio
    async def test_get_by_uid_not_found(self, service, mock_users_repo):
        """Test get_by_uid returns None when not found."""

        mock_users_repo.get_by_uid.return_value = None

        result = await service.get_by_uid("nonexistent-uid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, service, mock_users_repo, mock_user):
        """Test get_all returns paginated users."""

        mock_users_repo.search.return_value = ([mock_user], 1)
        mock_users_repo.get_user_role_names_bulk.return_value = {1: ["DOCENTE"]}

        filters = UserFilters(search=None)
        pagination = PaginationParams(page=1, limit=10)
        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 1
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_create_user_as_admin(
        self, service, mock_users_repo, mock_audit_service, mock_user
    ):
        """Test create_user succeeds when requester is ADMIN."""

        requester = MagicMock()
        requester.uid = "admin-uid"

        admin_user = MagicMock()
        admin_user.id = 99
        admin_user.uid = "admin-uid"

        mock_users_repo.get_by_uid.side_effect = [admin_user, mock_user]
        mock_users_repo.get_user_role_names.side_effect = [["ADMIN"], ["DOCENTE"]]
        mock_users_repo.find_or_create_user.return_value = (mock_user, True)

        role_docente = MagicMock()
        role_docente.id = 1
        role_docente.name = "DOCENTE"
        mock_users_repo.get_roles_by_names.return_value = [role_docente]

        data = UserCreate(
            email="new@example.com",
            name="New User",
            roles=[RoleName.DOCENTE],
        )

        result = await service.create_user(data, requester)

        assert result is not None
        mock_users_repo.replace_user_roles.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_as_director_with_docente_role(
        self, service, mock_users_repo, mock_user
    ):
        """Test create_user succeeds when DIRECTOR creates DOCENTE."""

        requester = MagicMock()
        requester.uid = "director-uid"

        director_user = MagicMock()
        director_user.id = 99
        director_user.uid = "director-uid"

        mock_users_repo.get_by_uid.side_effect = [director_user, mock_user]
        mock_users_repo.get_user_role_names.side_effect = [
            ["DIRECTOR DE DEPARTAMENTO"],
            ["DOCENTE"],
        ]
        mock_users_repo.find_or_create_user.return_value = (mock_user, True)

        role_docente = MagicMock()
        role_docente.id = 1
        role_docente.name = "DOCENTE"
        mock_users_repo.get_roles_by_names.return_value = [role_docente]

        data = UserCreate(
            email="teacher@example.com",
            name="Teacher",
            roles=[RoleName.DOCENTE],
        )

        result = await service.create_user(data, requester)

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_user_as_director_with_admin_role_raises(
        self, service, mock_users_repo
    ):
        """Test create_user raises when DIRECTOR tries to create ADMIN."""

        requester = MagicMock()
        requester.uid = "director-uid"

        director_user = MagicMock()
        director_user.id = 99
        mock_users_repo.get_by_uid.return_value = director_user
        mock_users_repo.get_user_role_names.return_value = ["DIRECTOR DE DEPARTAMENTO"]

        data = UserCreate(
            email="admin@example.com",
            name="Admin",
            roles=[RoleName.ADMIN],
        )

        with pytest.raises(PermissionDeniedError):
            await service.create_user(data, requester)

    @pytest.mark.asyncio
    async def test_create_user_without_permission_raises(
        self, service, mock_users_repo
    ):
        """Test create_user raises when user has no permission."""

        requester = MagicMock()
        requester.uid = "user-uid"

        regular_user = MagicMock()
        regular_user.id = 99
        mock_users_repo.get_by_uid.return_value = regular_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        data = UserCreate(
            email="new@example.com",
            name="New User",
            roles=[RoleName.DOCENTE],
        )

        with pytest.raises(PermissionDeniedError):
            await service.create_user(data, requester)

    @pytest.mark.asyncio
    async def test_create_user_with_invalid_role_raises(
        self, service, mock_users_repo, mock_user
    ):
        """Test create_user raises when role doesn't exist in DB."""

        requester = MagicMock()
        requester.uid = "admin-uid"

        admin_user = MagicMock()
        admin_user.id = 99
        mock_users_repo.get_by_uid.return_value = admin_user
        mock_users_repo.get_user_role_names.return_value = ["ADMIN"]
        mock_users_repo.find_or_create_user.return_value = (mock_user, True)

        # Return empty list to simulate role not found in DB
        # Use valid enum value but mock repo to return empty (simulating DB inconsistency)
        mock_users_repo.get_roles_by_names.return_value = []

        data = UserCreate(
            email="new@example.com",
            name="New User",
            roles=[RoleName.DOCENTE],
        )

        with pytest.raises(InvalidRoleError):
            await service.create_user(data, requester)

    @pytest.mark.asyncio
    async def test_update_user_success(self, service, mock_users_repo, mock_user):
        """Test update_user succeeds."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        data = UserUpdate(name="Updated Name")

        result = await service.update_user("test-uid-123", data)

        assert result is not None
        mock_users_repo.update_fields.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found_raises(self, service, mock_users_repo):
        """Test update_user raises when user not found."""

        mock_users_repo.get_by_uid.return_value = None

        data = UserUpdate(name="Updated Name")

        with pytest.raises(UserNotFoundError):
            await service.update_user("nonexistent-uid", data)

    @pytest.mark.asyncio
    async def test_update_user_with_roles(self, service, mock_users_repo, mock_user):
        """Test update_user with role changes."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        role = MagicMock()
        role.id = 1
        role.name = "ADMIN"
        mock_users_repo.get_roles_by_names.return_value = [role]

        data = UserUpdate(roles=[RoleName.ADMIN])

        result = await service.update_user("test-uid-123", data)

        assert result is not None
        mock_users_repo.replace_user_roles.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_with_invalid_roles_raises(
        self, service, mock_users_repo, mock_user
    ):
        """Test update_user raises when roles don't exist in DB."""

        mock_users_repo.get_by_uid.return_value = mock_user

        # Return empty list to simulate role not found in DB
        # Use valid enum value but mock repo to return empty (simulating DB inconsistency)
        mock_users_repo.get_roles_by_names.return_value = []

        data = UserUpdate(roles=[RoleName.DOCENTE])  # Valid enum but repo returns empty

        with pytest.raises(InvalidRoleError):
            await service.update_user("test-uid-123", data)

    @pytest.mark.asyncio
    async def test_replace_roles_as_admin(self, service, mock_users_repo, mock_user):
        """Test replace_roles succeeds when requester is ADMIN."""

        requester = MagicMock()
        requester.uid = "admin-uid"

        admin_user = MagicMock()
        admin_user.id = 99

        mock_users_repo.get_by_uid.side_effect = [admin_user, mock_user]
        mock_users_repo.get_user_role_names.side_effect = [["ADMIN"], ["DOCENTE"]]

        role = MagicMock()
        role.id = 1
        role.name = "ADMIN"
        mock_users_repo.get_roles_by_names.return_value = [role]

        payload = UserRolesUpdate(roles=[RoleName.ADMIN])

        result = await service.replace_roles("test-uid-123", payload, requester)

        assert result is not None

    @pytest.mark.asyncio
    async def test_replace_roles_as_own_user(self, service, mock_users_repo, mock_user):
        """Test replace_roles succeeds when user updates own roles."""

        requester = MagicMock()
        requester.uid = "test-uid-123"

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        role = MagicMock()
        role.id = 1
        role.name = "DOCENTE"
        mock_users_repo.get_roles_by_names.return_value = [role]

        payload = UserRolesUpdate(roles=[RoleName.DOCENTE])

        result = await service.replace_roles("test-uid-123", payload, requester)

        assert result is not None

    @pytest.mark.asyncio
    async def test_replace_roles_without_permission_raises(
        self, service, mock_users_repo, mock_user
    ):
        """Test replace_roles raises when user has no permission."""

        requester = MagicMock()
        requester.uid = "other-uid"

        other_user = MagicMock()
        other_user.id = 99
        mock_users_repo.get_by_uid.return_value = other_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        payload = UserRolesUpdate(roles=[RoleName.ADMIN])

        with pytest.raises(PermissionDeniedError):
            await service.replace_roles("test-uid-123", payload, requester)

    @pytest.mark.asyncio
    async def test_update_status_success(self, service, mock_users_repo, mock_user):
        """Test update_status succeeds."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        data = UserStatusUpdate(active=False)

        result = await service.update_status("test-uid-123", data)

        assert result is not None
        mock_users_repo.update_active.assert_called_once_with(mock_user, False)

    @pytest.mark.asyncio
    async def test_update_status_not_found_raises(self, service, mock_users_repo):
        """Test update_status raises when user not found."""

        mock_users_repo.get_by_uid.return_value = None

        data = UserStatusUpdate(active=False)

        with pytest.raises(UserNotFoundError):
            await service.update_status("nonexistent-uid", data)

    @pytest.mark.asyncio
    async def test_create_user_with_roles(self, service, mock_users_repo, mock_user):
        """Test create_user_with_roles creates user with specified roles."""

        mock_users_repo.find_or_create_user.return_value = (mock_user, True)
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        role = MagicMock()
        role.id = 1
        role.name = "DOCENTE"
        mock_users_repo.get_roles_by_names.return_value = [role]

        data = UserCreate(
            email="teacher@example.com",
            name="Teacher",
            roles=[RoleName.DOCENTE],
        )

        result = await service.create_user_with_roles(data, department_id=1)

        assert result is not None
        mock_users_repo.replace_user_roles.assert_called_once()
        mock_users_repo.create_teacher.assert_called_once()
