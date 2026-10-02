"""
Tests for UserService layer.
"""

from unittest.mock import MagicMock, AsyncMock
import pytest

from api.core.pagination import PaginationParams
from api.services.user_service import UserService
from api.schemas.user import (
    UserAdminUpdate,
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
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
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
    async def test_get_by_uid_resolves_faculty_for_a_dean(
        self, service, mock_users_repo, mock_user
    ):
        """Test a DECANO's faculty_id/faculty_name get resolved via the
        deans association, mirroring how a director's department resolves."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DECANO"]
        mock_users_repo.get_teacher_by_user_id.return_value = None
        mock_users_repo.get_dean_by_user_id.return_value = MagicMock(faculty_id=3)
        mock_users_repo.get_faculty_name.return_value = "Ingenierías"

        result = await service.get_by_uid("test-uid-123")

        assert result["faculty_id"] == 3
        assert result["faculty_name"] == "Ingenierías"
        assert result["department_id"] is None

    @pytest.mark.asyncio
    async def test_get_by_uid_non_dean_has_no_faculty(
        self, service, mock_users_repo, mock_user
    ):
        """Test a non-DECANO role never resolves a faculty."""

        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_users_repo.get_teacher_by_user_id.return_value = None

        result = await service.get_by_uid("test-uid-123")

        assert result["faculty_id"] is None
        assert result["faculty_name"] is None
        mock_users_repo.get_dean_by_user_id.assert_not_called()

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


def _role(role_id, name):
    role = MagicMock(id=role_id)
    role.name = name
    return role


class TestAdminUpdateUser:
    """Tests for UserService.admin_update_user, get_by_id and update_user_by_id."""

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository with a DOCENTE user and no conflicts."""

        repo = MagicMock()
        repo.get_user_role_names.return_value = ["DOCENTE"]
        repo.get_by_email.return_value = None
        repo.get_by_institutional_code.return_value = None
        repo.department_exists.return_value = True
        repo.get_director_by_user_id.return_value = None
        repo.get_dean_by_user_id.return_value = None
        return repo

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
    def user(self, mock_users_repo):
        """A linked (already logged in) DOCENTE user with a teacher record."""

        from api.models.user import UserModel

        user = MagicMock(spec=UserModel)
        user.id = 5
        user.uid = "firebase-uid"
        user.email = "old@ufps.edu.co"
        user.name = "Old Name"
        user.institutional_code = "1111"
        user.active = True
        user.avatar_url = None
        mock_users_repo.get.return_value = user
        mock_users_repo.get_teacher_by_user_id.return_value = MagicMock(
            department_id=1
        )
        return user

    @pytest.fixture
    def admin(self):
        """The acting administrator."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_by_id_when_missing_returns_none(self, service, mock_users_repo):
        mock_users_repo.get.return_value = None

        assert await service.get_by_id(404) is None

    @pytest.mark.asyncio
    async def test_get_by_id_found_returns_user(self, service, user):
        result = await service.get_by_id(5)

        assert result["id"] == 5

    @pytest.mark.asyncio
    async def test_get_by_id_of_a_director_returns_both_departments(
        self, service, mock_users_repo, user
    ):
        """Test a director's teacher department is reported apart from the one they direct.

        department_id resolves to the directed department (15), so an edit form
        prefilled with it would hide a teacher record left in another one (14).
        """

        mock_users_repo.get_user_role_names.return_value = [
            "DOCENTE",
            "DIRECTOR DE DEPARTAMENTO",
        ]
        mock_users_repo.get_director_by_user_id.return_value = MagicMock(
            department_id=15
        )
        user.teacher = MagicMock(id=146, department_id=14)

        result = await service.get_by_id(5)

        assert result["department_id"] == 15
        assert result["teacher_department_id"] == 14

    @pytest.mark.asyncio
    async def test_get_by_id_without_teacher_record_has_no_teacher_department(
        self, service, user
    ):
        user.teacher = None

        result = await service.get_by_id(5)

        assert result["teacher_id"] is None
        assert result["teacher_department_id"] is None

    @pytest.mark.asyncio
    async def test_admin_update_moves_a_directors_teacher_record(
        self, service, mock_users_repo, user, admin
    ):
        """Test sending the directed department moves a teacher record left elsewhere."""

        mock_users_repo.get_user_role_names.return_value = [
            "DOCENTE",
            "DIRECTOR DE DEPARTAMENTO",
        ]
        mock_users_repo.get_director_by_user_id.return_value = MagicMock(
            department_id=15
        )
        teacher = MagicMock(department_id=14)
        mock_users_repo.get_teacher_by_user_id.return_value = teacher

        await service.admin_update_user(5, UserAdminUpdate(department_id=15), admin)

        mock_users_repo.set_teacher_department.assert_called_once_with(teacher, 15)

    @pytest.mark.asyncio
    async def test_update_user_by_id_reaches_a_user_without_uid(
        self, service, mock_users_repo, user
    ):
        """Test roles can be changed for a user who never logged in."""

        user.uid = None
        mock_users_repo.get_roles_by_names.return_value = [_role(2, "DECANO")]

        await service.update_user_by_id(5, UserUpdate(roles=[RoleName.DECANO]))

        mock_users_repo.get.assert_called_once_with(5)
        mock_users_repo.get_by_uid.assert_not_called()
        mock_users_repo.replace_user_roles.assert_called_once_with(5, [2])

    @pytest.mark.asyncio
    async def test_update_user_by_id_when_missing_raises(self, service, mock_users_repo):
        mock_users_repo.get.return_value = None

        with pytest.raises(UserNotFoundError):
            await service.update_user_by_id(404, UserUpdate(name="X"))

    @pytest.mark.asyncio
    async def test_admin_update_when_missing_returns_none(
        self, service, mock_users_repo, admin
    ):
        mock_users_repo.get.return_value = None

        result = await service.admin_update_user(404, UserAdminUpdate(name="X"), admin)

        assert result is None
        mock_users_repo.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_update_changes_name_email_and_code(
        self, service, mock_users_repo, mock_audit_service, user, admin
    ):
        """Test the fields are written once and the audit names each change."""

        data = UserAdminUpdate(
            name="New Name", email="NEW@ufps.edu.co", institutional_code="2222"
        )

        await service.admin_update_user(5, data, admin)

        written = mock_users_repo.assign_fields.call_args.args[1]
        assert written["name"] == "New Name"
        assert written["email"] == "new@ufps.edu.co"
        assert written["institutional_code"] == "2222"
        mock_users_repo.commit.assert_called_once()
        description = mock_audit_service.log.call_args.kwargs["description"]
        assert "email cambió" in description
        assert "institutional_code cambió" in description

    @pytest.mark.asyncio
    async def test_admin_update_deactivates_the_user(
        self, service, mock_users_repo, user, admin
    ):
        await service.admin_update_user(5, UserAdminUpdate(active=False), admin)

        assert mock_users_repo.assign_fields.call_args.args[1] == {"active": False}

    @pytest.mark.asyncio
    async def test_admin_update_email_of_linked_user_clears_uid(
        self, service, mock_users_repo, user, admin
    ):
        """Test a new email unlinks Firebase so the next login re-links."""

        await service.admin_update_user(
            5, UserAdminUpdate(email="new@ufps.edu.co"), admin
        )

        written = mock_users_repo.assign_fields.call_args.args[1]
        assert "uid" in written
        assert written["uid"] is None

    @pytest.mark.asyncio
    async def test_admin_update_email_of_unlinked_user_keeps_uid_untouched(
        self, service, mock_users_repo, user, admin
    ):
        user.uid = None

        await service.admin_update_user(
            5, UserAdminUpdate(email="new@ufps.edu.co"), admin
        )

        assert "uid" not in mock_users_repo.assign_fields.call_args.args[1]

    @pytest.mark.asyncio
    async def test_admin_update_same_email_does_not_unlink(
        self, service, mock_users_repo, user, admin
    ):
        await service.admin_update_user(
            5, UserAdminUpdate(email="old@ufps.edu.co"), admin
        )

        mock_users_repo.assign_fields.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_update_email_taken_by_another_user_raises(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.get_by_email.return_value = MagicMock(id=6)

        with pytest.raises(UserAlreadyExistsError):
            await service.admin_update_user(
                5, UserAdminUpdate(email="taken@ufps.edu.co"), admin
            )

        mock_users_repo.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_update_code_taken_by_another_user_raises(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.get_by_institutional_code.return_value = MagicMock(id=6)

        with pytest.raises(ResourceAlreadyExistsError):
            await service.admin_update_user(
                5, UserAdminUpdate(institutional_code="3333"), admin
            )

    @pytest.mark.asyncio
    async def test_admin_update_replaces_roles(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.get_roles_by_names.return_value = [
            _role(1, "DOCENTE"),
            _role(4, "DECANO"),
        ]

        await service.admin_update_user(
            5, UserAdminUpdate(roles=[RoleName.DOCENTE, RoleName.DECANO]), admin
        )

        mock_users_repo.replace_user_roles.assert_called_once_with(5, [1, 4])

    @pytest.mark.asyncio
    async def test_admin_update_with_unknown_role_raises(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.get_roles_by_names.return_value = []

        with pytest.raises(InvalidRoleError):
            await service.admin_update_user(
                5, UserAdminUpdate(roles=[RoleName.DECANO]), admin
            )

    @pytest.mark.asyncio
    async def test_admin_cannot_remove_their_own_admin_role(
        self, service, mock_users_repo, user
    ):
        mock_users_repo.get_user_role_names.return_value = ["ADMIN"]
        mock_users_repo.get_roles_by_names.return_value = [_role(1, "DOCENTE")]

        with pytest.raises(ValidationError):
            await service.admin_update_user(
                5, UserAdminUpdate(roles=[RoleName.DOCENTE]), {"id": 5}
            )

        mock_users_repo.replace_user_roles.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_update_moves_the_teacher_to_another_department(
        self, service, mock_users_repo, user, admin
    ):
        teacher = mock_users_repo.get_teacher_by_user_id.return_value

        await service.admin_update_user(5, UserAdminUpdate(department_id=3), admin)

        mock_users_repo.set_teacher_department.assert_called_once_with(teacher, 3)

    @pytest.mark.asyncio
    async def test_admin_update_null_department_clears_it(
        self, service, mock_users_repo, user, admin
    ):
        teacher = mock_users_repo.get_teacher_by_user_id.return_value

        await service.admin_update_user(
            5, UserAdminUpdate(department_id=None), admin
        )

        mock_users_repo.set_teacher_department.assert_called_once_with(teacher, None)

    @pytest.mark.asyncio
    async def test_admin_update_department_for_non_teacher_raises(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.get_user_role_names.return_value = ["DECANO"]

        with pytest.raises(ValidationError):
            await service.admin_update_user(5, UserAdminUpdate(department_id=3), admin)

        mock_users_repo.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_update_unknown_department_raises(
        self, service, mock_users_repo, user, admin
    ):
        mock_users_repo.department_exists.return_value = False

        with pytest.raises(ResourceNotFoundError):
            await service.admin_update_user(
                5, UserAdminUpdate(department_id=999), admin
            )

    @pytest.mark.asyncio
    async def test_admin_update_granting_docente_creates_teacher_in_department(
        self, service, mock_users_repo, user, admin
    ):
        """Test a user turned DOCENTE gets a teacher record in the given department."""

        mock_users_repo.get_user_role_names.return_value = ["DECANO"]
        mock_users_repo.get_teacher_by_user_id.return_value = None
        mock_users_repo.get_roles_by_names.return_value = [_role(1, "DOCENTE")]

        await service.admin_update_user(
            5, UserAdminUpdate(roles=[RoleName.DOCENTE], department_id=3), admin
        )

        assert mock_users_repo.create_teacher.call_args.kwargs["department_id"] == 3
