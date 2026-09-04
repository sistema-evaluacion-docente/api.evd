"""Tests for DirectorService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.models.director import DirectorsModel
from api.schemas.director import DirectorCreate, DirectorFilters, DirectorUpdate
from api.services.director_service import DirectorService


class TestDirectorService:
    """Test suite for DirectorService."""

    @pytest.fixture
    def mock_directors_repo(self):
        """Mock DirectorsRepository."""
        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_departments_repo(self):
        """Mock DepartmentsRepository."""
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
        service.create_user_with_roles = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_directors_repo,
        mock_users_repo,
        mock_departments_repo,
        mock_audit_service,
        mock_user_service,
    ):
        """Create service instance with mocked dependencies."""
        return DirectorService(
            mock_directors_repo,
            mock_users_repo,
            mock_departments_repo,
            mock_audit_service,
            mock_user_service,
        )

    @pytest.fixture
    def mock_director(self):
        """Mock DirectorsModel instance."""
        director = MagicMock(spec=DirectorsModel)
        director.id = 1
        director.user_id = 10
        director.department_id = 1
        director.active = True
        director.user = MagicMock()
        director.user.institutional_code = "12345"
        director.created_at = "2024-01-01T00:00:00Z"
        director.updated_at = "2024-01-01T00:00:00Z"
        return director

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""
        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_directors(
        self, service, mock_directors_repo, mock_director
    ):
        """Test get_all returns paginated directors."""
        mock_directors_repo.search.return_value = ([mock_director], 1)

        # Mock user con valores reales
        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.avatar_url = None
        service.users_repository.get.return_value = mock_user

        # Mock department con valores reales
        mock_department = MagicMock()
        mock_department.id = 1
        mock_department.name = "Computer Science"
        mock_department.code = "CS"
        service.departments_repository.get.return_value = mock_department

        filters = DirectorFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_directors_repo, mock_director):
        """Test get_by_id returns director dict when found."""
        mock_directors_repo.get.return_value = mock_director

        # Mock user con valores reales
        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.avatar_url = None
        service.users_repository.get.return_value = mock_user

        # Mock department con valores reales
        mock_department = MagicMock()
        mock_department.id = 1
        mock_department.name = "Computer Science"
        mock_department.code = "CS"
        service.departments_repository.get.return_value = mock_department

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_directors_repo):
        """Test get_by_id returns None when not found."""
        mock_directors_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_director_success(
        self,
        service,
        mock_directors_repo,
        mock_departments_repo,
        mock_users_repo,
        mock_user_service,
        mock_audit_service,
        mock_director,
        current_user,
    ):
        """Test create succeeds with valid data."""
        mock_department = MagicMock()
        mock_department.id = 1
        mock_department.name = "CS"
        mock_department.code = "CS"
        mock_departments_repo.get.return_value = mock_department

        mock_users_repo.get_by_email.return_value = None
        mock_directors_repo.get_by_department_id.return_value = None
        mock_directors_repo.get_by_institutional_code.return_value = None
        mock_user_service.create_user_with_roles.return_value = {"id": 10}
        mock_directors_repo.create.return_value = mock_director
        mock_directors_repo.get.return_value = mock_director

        # Mock user con valores reales
        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.avatar_url = None
        mock_users_repo.get.return_value = mock_user

        data = DirectorCreate(
            email="test@example.com",
            name="Test User",
            institutional_code="12345",
            department_id=1,
        )

        result = await service.create(data, current_user)

        assert result is not None
        mock_user_service.create_user_with_roles.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_director_department_not_found(
        self, service, mock_departments_repo, current_user
    ):
        """Test create raises when department not found."""
        mock_departments_repo.get.return_value = None

        data = DirectorCreate(
            email="test@example.com",
            name="Test User",
            institutional_code="12345",
            department_id=999,
        )

        with pytest.raises(ResourceNotFoundError):
            await service.create(data, current_user)

    @pytest.mark.asyncio
    async def test_create_director_user_already_exists(
        self, service, mock_departments_repo, mock_users_repo, current_user
    ):
        """Test create raises when user email already exists."""
        mock_departments_repo.get.return_value = MagicMock(id=1, name="CS")
        mock_users_repo.get_by_email.return_value = MagicMock(id=10)

        data = DirectorCreate(
            email="existing@example.com",
            name="Test User",
            institutional_code="12345",
            department_id=1,
        )

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, current_user)

    @pytest.mark.asyncio
    async def test_create_director_department_already_has_director(
        self,
        service,
        mock_departments_repo,
        mock_users_repo,
        mock_directors_repo,
        current_user,
    ):
        """Test create raises when department already has a director."""
        mock_departments_repo.get.return_value = MagicMock(id=1, name="CS")
        mock_users_repo.get_by_email.return_value = None
        mock_directors_repo.get_by_department_id.return_value = MagicMock(id=1)

        data = DirectorCreate(
            email="test@example.com",
            name="Test User",
            institutional_code="12345",
            department_id=1,
        )

        with pytest.raises(ValidationError) as exc_info:
            await service.create(data, current_user)

        assert "Este departamento ya tiene un director asignado" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_director_success(
        self,
        service,
        mock_directors_repo,
        mock_audit_service,
        mock_director,
        current_user,
    ):
        """Test update succeeds when director exists."""
        mock_directors_repo.get.return_value = mock_director
        mock_directors_repo.update_director.return_value = mock_director
        mock_directors_repo.get_by_department_id.return_value = None
        mock_directors_repo.get_by_institutional_code.return_value = None
        mock_directors_repo.get_by_user_id.return_value = None

        # Mock user con valores reales
        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.avatar_url = None
        service.users_repository.get.return_value = mock_user

        # Mock department con valores reales
        mock_department = MagicMock()
        mock_department.id = 1
        mock_department.name = "Computer Science"
        mock_department.code = "CS"
        service.departments_repository.get.return_value = mock_department

        data = DirectorUpdate(active=False)

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_directors_repo.update_director.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_director_not_found(
        self, service, mock_directors_repo, current_user
    ):
        """Test update returns None when director not found."""
        mock_directors_repo.get.return_value = None

        data = DirectorUpdate(active=False)

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_director_success(
        self,
        service,
        mock_directors_repo,
        mock_audit_service,
        mock_director,
        current_user,
    ):
        """Test delete succeeds when director exists."""
        mock_directors_repo.get.return_value = mock_director

        result = await service.delete(1, current_user)

        assert result is not None
        mock_directors_repo.delete_director.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_director_not_found(
        self, service, mock_directors_repo, current_user
    ):
        """Test delete returns None when director not found."""
        mock_directors_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_director_department_already_assigned(
        self, service, mock_directors_repo, mock_director, current_user
    ):
        """Test moving a director to a department that already has one fails."""
        mock_directors_repo.get.return_value = mock_director
        mock_directors_repo.get_by_department_id.return_value = MagicMock(id=99)

        data = DirectorUpdate(department_id=2)

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, data, current_user)

    @pytest.mark.asyncio
    async def test_update_director_institutional_code_taken(
        self, service, mock_directors_repo, mock_director, current_user
    ):
        """Test reusing another director's institutional code fails."""
        mock_directors_repo.get.return_value = mock_director
        mock_directors_repo.get_by_institutional_code.return_value = MagicMock(id=99)

        data = DirectorUpdate(institutional_code="99999")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, data, current_user)

    @pytest.mark.asyncio
    async def test_update_director_user_already_director_elsewhere(
        self, service, mock_directors_repo, mock_director, current_user
    ):
        """Test reassigning a user who directs a different department fails."""
        mock_directors_repo.get.return_value = mock_director
        mock_directors_repo.get_by_department_id.return_value = None
        other_directorship = MagicMock(department_id=55)
        mock_directors_repo.get_by_user_id.return_value = other_directorship

        data = DirectorUpdate(user_id=20)

        with pytest.raises(ValueError):
            await service.update(1, data, current_user)

    @pytest.mark.asyncio
    async def test_assign_director_department_not_found(
        self, service, mock_departments_repo, current_user
    ):
        """Test assigning to a missing department raises."""
        mock_departments_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.assign_director(999, 10, current_user)

    @pytest.mark.asyncio
    async def test_assign_director_user_not_found(
        self, service, mock_departments_repo, mock_users_repo, current_user
    ):
        """Test assigning a missing user raises."""
        mock_departments_repo.get.return_value = MagicMock(id=1, name="Sistemas")
        mock_users_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.assign_director(1, 999, current_user)

    @pytest.mark.asyncio
    async def test_assign_director_grants_the_role_when_missing(
        self,
        service,
        mock_departments_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_user_service,
        mock_director,
        current_user,
    ):
        """Test a user without the director role gets it added before assigning."""
        department = MagicMock(id=1, code="SIS")
        department.name = "Sistemas"
        mock_departments_repo.get.return_value = department
        user = MagicMock(
            id=10, uid="uid-10", email="ana@ufps.edu.co", avatar_url=None
        )
        user.name = "Ana"
        mock_users_repo.get.return_value = user
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_user_service.update_user = AsyncMock()
        mock_directors_repo.assign_director.return_value = mock_director
        mock_directors_repo.get.return_value = mock_director

        result = await service.assign_director(1, 10, current_user)

        assert result is not None
        mock_user_service.update_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_director_keeps_the_role_when_already_present(
        self,
        service,
        mock_departments_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_user_service,
        mock_director,
        current_user,
    ):
        """Test a user who already has the role is not updated again."""
        department = MagicMock(id=1, code="SIS")
        department.name = "Sistemas"
        mock_departments_repo.get.return_value = department
        user = MagicMock(
            id=10, uid="uid-10", email="ana@ufps.edu.co", avatar_url=None
        )
        user.name = "Ana"
        mock_users_repo.get.return_value = user
        mock_users_repo.get_user_role_names.return_value = [
            "DIRECTOR DE DEPARTAMENTO"
        ]
        mock_user_service.update_user = AsyncMock()
        mock_directors_repo.assign_director.return_value = mock_director
        mock_directors_repo.get.return_value = mock_director

        await service.assign_director(1, 10, current_user)

        mock_user_service.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_unassign_director_department_not_found(
        self, service, mock_departments_repo, current_user
    ):
        """Test unassigning from a missing department raises."""
        mock_departments_repo.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.unassign_director(999, current_user)

    @pytest.mark.asyncio
    async def test_unassign_director_without_a_current_director(
        self, service, mock_departments_repo, mock_directors_repo, current_user
    ):
        """Test unassigning a department with no director returns None."""
        mock_departments_repo.get.return_value = MagicMock(id=1, name="Sistemas")
        mock_directors_repo.unassign_director.return_value = None

        result = await service.unassign_director(1, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_unassign_director_success(
        self,
        service,
        mock_departments_repo,
        mock_directors_repo,
        mock_audit_service,
        mock_director,
        current_user,
    ):
        """Test a successful unassignment logs the audit and returns the director."""
        mock_departments_repo.get.return_value = MagicMock(id=1, name="Sistemas")
        mock_directors_repo.unassign_director.return_value = mock_director

        result = await service.unassign_director(1, current_user)

        assert result is not None
        mock_audit_service.log.assert_called_once()
