"""
Tests for FacultyService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.models.faculty import FacultyModel
from api.schemas.faculty import (
    FacultyCreate,
    FacultyFilters,
    FacultyUpdate,
)
from api.schemas.user import RoleName
from api.services.faculty_service import FacultyService


class TestFacultyService:
    """Test suite for FacultyService."""

    @pytest.fixture
    def mock_faculties_repo(self):
        """Mock FacultiesRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        repo.get_deans_by_faculty_ids.return_value = {}
        repo.get_dean_with_user_by_faculty_id.return_value = None
        return repo

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
    def mock_user_service(self):
        """Mock UserService."""

        service = MagicMock()
        service.update_user = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self, mock_faculties_repo, mock_users_repo, mock_audit_service, mock_user_service
    ):
        """Create service instance with mocked dependencies."""

        return FacultyService(
            mock_faculties_repo,
            mock_users_repo,
            mock_audit_service,
            mock_user_service,
        )

    @pytest.fixture
    def mock_faculty(self):
        """Mock FacultyModel instance."""

        faculty = MagicMock(spec=FacultyModel)
        faculty.id = 1
        faculty.name = "Engineering"
        faculty.code = "ENG"
        faculty.active = True
        faculty.created_at = "2024-01-01T00:00:00Z"
        faculty.updated_at = "2024-01-01T00:00:00Z"
        return faculty

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_faculties(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test get_all returns paginated faculties."""

        mock_faculties_repo.search.return_value = ([mock_faculty], 1)
        mock_faculties_repo.get_department_counts.return_value = {}

        filters = FacultyFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1
        assert result["items"][0]["department_count"] == 0

    @pytest.mark.asyncio
    async def test_get_all_with_department_counts(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test get_all includes department_count."""

        mock_faculties_repo.search.return_value = ([mock_faculty], 1)
        mock_faculties_repo.get_department_counts.return_value = {1: 5}

        filters = FacultyFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"][0]["department_count"] == 5

    @pytest.mark.asyncio
    async def test_get_all_includes_dean_when_assigned(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test get_all embeds the dean summary for a faculty that has one."""

        mock_faculties_repo.search.return_value = ([mock_faculty], 1)
        mock_faculties_repo.get_department_counts.return_value = {}
        mock_faculties_repo.get_deans_by_faculty_ids.return_value = {
            1: {"id": 10, "name": "Decano", "avatar_url": None}
        }

        filters = FacultyFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"][0]["dean"].id == 10

    @pytest.mark.asyncio
    async def test_get_all_dean_is_none_when_unassigned(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test get_all's dean is None for a faculty without one."""

        mock_faculties_repo.search.return_value = ([mock_faculty], 1)
        mock_faculties_repo.get_department_counts.return_value = {}

        filters = FacultyFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"][0]["dean"] is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_faculties_repo, mock_faculty):
        """Test get_by_id returns faculty dict when found."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["department_count"] == 0
        assert result["dean"] is None

    @pytest.mark.asyncio
    async def test_get_by_id_includes_dean_when_assigned(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test get_by_id embeds the dean summary when the faculty has one."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}
        mock_faculties_repo.get_dean_with_user_by_faculty_id.return_value = {
            "id": 10,
            "name": "Decano",
            "avatar_url": None,
        }

        result = await service.get_by_id(1)

        assert result["dean"].id == 10

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_faculties_repo):
        """Test get_by_id returns None when not found."""

        mock_faculties_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_faculty_success(
        self,
        service,
        mock_faculties_repo,
        mock_audit_service,
        mock_faculty,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_faculties_repo.get_by_code.return_value = None
        mock_faculties_repo.create_faculty.return_value = mock_faculty

        data = FacultyCreate(name="Engineering", code="ENG")

        result = await service.create(data, current_user)

        assert result is not None
        assert result["dean"] is None
        mock_faculties_repo.create_faculty.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_faculty_duplicate_code_raises(
        self, service, mock_faculties_repo, mock_faculty
    ):
        """Test create raises when code already exists."""

        mock_faculties_repo.get_by_code.return_value = mock_faculty

        data = FacultyCreate(name="Engineering", code="ENG")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_faculty_success(
        self,
        service,
        mock_faculties_repo,
        mock_audit_service,
        mock_faculty,
        current_user,
    ):
        """Test update succeeds when faculty exists."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_by_code.return_value = None
        mock_faculties_repo.update_faculty.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}

        data = FacultyUpdate(name="Updated Name")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_faculties_repo.update_faculty.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_faculty_not_found(
        self, service, mock_faculties_repo, current_user
    ):
        """Test update returns None when faculty not found."""

        mock_faculties_repo.get.return_value = None

        data = FacultyUpdate(name="Updated Name")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_faculty_duplicate_code_raises(
        self, service, mock_faculties_repo, mock_faculty, current_user
    ):
        """Test update raises when new code already exists."""

        other_faculty = MagicMock(spec=FacultyModel)
        other_faculty.id = 2
        other_faculty.code = "OTHER"

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_by_code.return_value = other_faculty

        data = FacultyUpdate(code="OTHER")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, data, current_user)

    @pytest.mark.asyncio
    async def test_update_faculty_describes_a_code_and_active_change(
        self, service, mock_faculties_repo, mock_audit_service, mock_faculty, current_user
    ):
        """Test the audit description names every field that actually changed."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_by_code.return_value = None
        mock_faculties_repo.update_faculty.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}

        data = FacultyUpdate(code="ENG2", active=False)

        await service.update(1, data, current_user)

        description = mock_audit_service.log.call_args.kwargs["description"]
        assert "code cambió" in description
        assert "active cambió" in description

    @pytest.mark.asyncio
    async def test_update_faculty_with_no_actual_changes(
        self, service, mock_faculties_repo, mock_audit_service, mock_faculty, current_user
    ):
        """Test the audit description says so when nothing actually changed."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.update_faculty.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}

        data = FacultyUpdate(name="Engineering")

        await service.update(1, data, current_user)

        description = mock_audit_service.log.call_args.kwargs["description"]
        assert description.endswith("No se realizaron cambios")

    @pytest.mark.asyncio
    async def test_delete_faculty_success(
        self,
        service,
        mock_faculties_repo,
        mock_audit_service,
        mock_faculty,
        current_user,
    ):
        """Test delete succeeds when no departments."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.has_departments.return_value = False

        result = await service.delete(1, current_user)

        assert result is not None
        mock_faculties_repo.delete_faculty.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_faculty_not_found(
        self, service, mock_faculties_repo, current_user
    ):
        """Test delete returns None when faculty not found."""

        mock_faculties_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_faculty_with_departments_raises(
        self, service, mock_faculties_repo, mock_faculty, current_user
    ):
        """Test delete raises when faculty has departments."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.has_departments.return_value = True

        with pytest.raises(ValidationError):
            await service.delete(1, current_user)

    @pytest.mark.asyncio
    async def test_assign_dean_faculty_not_found(
        self, service, mock_faculties_repo, current_user
    ):
        """Test assigning a dean to a missing faculty raises."""

        mock_faculties_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.assign_dean(999, 10, current_user)

    @pytest.mark.asyncio
    async def test_assign_dean_user_not_found(
        self, service, mock_faculties_repo, mock_users_repo, mock_faculty, current_user
    ):
        """Test assigning a missing user as dean raises."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_users_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.assign_dean(1, 999, current_user)

    @pytest.mark.asyncio
    async def test_assign_dean_grants_the_role_when_missing(
        self,
        service,
        mock_faculties_repo,
        mock_users_repo,
        mock_user_service,
        mock_faculty,
        current_user,
    ):
        """Test a user without the DECANO role gets it added before assigning."""

        mock_faculties_repo.get.return_value = mock_faculty
        user = MagicMock(id=10, uid="uid-10")
        mock_users_repo.get.return_value = user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_dean = MagicMock(id=1, user_id=10, faculty_id=1, active=True)
        mock_faculties_repo.assign_dean.return_value = mock_dean

        result = await service.assign_dean(1, 10, current_user)

        assert result is not None
        mock_user_service.update_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_dean_keeps_the_role_when_already_present(
        self,
        service,
        mock_faculties_repo,
        mock_users_repo,
        mock_user_service,
        mock_faculty,
        current_user,
    ):
        """Test a user who already has DECANO is not updated again."""

        mock_faculties_repo.get.return_value = mock_faculty
        user = MagicMock(id=10, uid="uid-10")
        mock_users_repo.get.return_value = user
        mock_users_repo.get_user_role_names.return_value = [RoleName.DECANO.value]
        mock_dean = MagicMock(id=1, user_id=10, faculty_id=1, active=True)
        mock_faculties_repo.assign_dean.return_value = mock_dean

        await service.assign_dean(1, 10, current_user)

        mock_user_service.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_unassign_dean_faculty_not_found(
        self, service, mock_faculties_repo, current_user
    ):
        """Test unassigning from a missing faculty raises."""

        mock_faculties_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.unassign_dean(999, current_user)

    @pytest.mark.asyncio
    async def test_unassign_dean_without_a_current_dean(
        self, service, mock_faculties_repo, mock_faculty, current_user
    ):
        """Test unassigning a faculty with no dean returns None."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_dean_by_faculty_id.return_value = None

        result = await service.unassign_dean(1, current_user)

        assert result is None
        mock_faculties_repo.delete_dean.assert_not_called()

    @pytest.mark.asyncio
    async def test_unassign_dean_success(
        self,
        service,
        mock_faculties_repo,
        mock_users_repo,
        mock_audit_service,
        mock_faculty,
        current_user,
    ):
        """A successful unassignment deletes the row outright and logs the audit."""

        mock_dean = MagicMock(id=1, user_id=10, faculty_id=1, active=True)
        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_dean_by_faculty_id.return_value = mock_dean
        mock_users_repo.get.return_value = None

        result = await service.unassign_dean(1, current_user)

        assert result is not None
        mock_faculties_repo.delete_dean.assert_called_once_with(mock_dean)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_unassign_dean_removes_the_dean_role(
        self,
        service,
        mock_faculties_repo,
        mock_users_repo,
        mock_user_service,
        mock_faculty,
        current_user,
    ):
        """Unassigning drops DECANO, keeping the user's other roles."""

        mock_dean = MagicMock(id=1, user_id=10, faculty_id=1, active=True)
        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_dean_by_faculty_id.return_value = mock_dean
        mock_users_repo.get.return_value = MagicMock(id=10, uid="uid-10")
        mock_users_repo.get_user_role_names.return_value = [
            "DOCENTE",
            RoleName.DECANO.value,
        ]

        await service.unassign_dean(1, current_user)

        from api.schemas.user import UserUpdate

        mock_user_service.update_user.assert_awaited_once_with(
            "uid-10", UserUpdate(roles=["DOCENTE"])
        )

    @pytest.mark.asyncio
    async def test_unassign_dean_keeps_the_role_if_it_is_the_users_only_one(
        self,
        service,
        mock_faculties_repo,
        mock_users_repo,
        mock_user_service,
        mock_faculty,
        current_user,
    ):
        """A user can't be left with zero roles, so the last one stays put."""

        mock_dean = MagicMock(id=1, user_id=10, faculty_id=1, active=True)
        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_dean_by_faculty_id.return_value = mock_dean
        mock_users_repo.get.return_value = MagicMock(id=10, uid="uid-10")
        mock_users_repo.get_user_role_names.return_value = [RoleName.DECANO.value]

        await service.unassign_dean(1, current_user)

        mock_user_service.update_user.assert_not_awaited()
