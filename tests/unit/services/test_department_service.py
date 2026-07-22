"""
Tests for DepartmentService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.models.department import DepartmentModel
from api.schemas.department import (
    DepartmentCreate,
    DepartmentFilters,
    DepartmentUpdate,
)
from api.services.department_service import DepartmentService


class TestDepartmentService:
    """Test suite for DepartmentService."""

    @pytest.fixture
    def mock_departments_repo(self):
        """Mock DepartmentsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
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
    def service(self, mock_departments_repo, mock_users_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return DepartmentService(
            mock_departments_repo,
            mock_users_repo,
            mock_audit_service,
        )

    @pytest.fixture
    def mock_department(self):
        """Mock DepartmentModel instance."""

        dept = MagicMock(spec=DepartmentModel)
        dept.id = 1
        dept.code = "CS"
        dept.name = "Computer Science"
        dept.faculty_id = 1
        dept.active = True
        dept.created_at = "2024-01-01T00:00:00Z"
        dept.updated_at = "2024-01-01T00:00:00Z"
        return dept

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_departments(
        self, service, mock_departments_repo, mock_department
    ):
        """Test get_all returns paginated departments."""

        mock_departments_repo.search.return_value = ([mock_department], 1)
        mock_departments_repo.get_directors_by_department_ids.return_value = {}
        mock_departments_repo.count_teachers_by_department_ids.return_value = {}

        filters = DepartmentFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1
        assert result["items"][0]["teacher_count"] == 0

    @pytest.mark.asyncio
    async def test_get_all_with_director_and_teachers(
        self, service, mock_departments_repo, mock_department
    ):
        """Test get_all includes director and teacher_count."""

        mock_departments_repo.search.return_value = ([mock_department], 1)
        mock_departments_repo.get_directors_by_department_ids.return_value = {
            1: {"id": 10, "name": "Dir", "avatar_url": None}
        }
        mock_departments_repo.count_teachers_by_department_ids.return_value = {1: 5}

        filters = DepartmentFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"][0]["director"].id == 10
        assert result["items"][0]["teacher_count"] == 5

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, service, mock_departments_repo, mock_department
    ):
        """Test get_by_id returns department dict when found."""

        mock_departments_repo.get_by_id.return_value = mock_department
        mock_departments_repo.get_director_by_department_id.return_value = None
        mock_departments_repo.count_teachers_by_department_ids.return_value = {}

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["teacher_count"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_departments_repo):
        """Test get_by_id returns None when not found."""

        mock_departments_repo.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_department_success(
        self,
        service,
        mock_departments_repo,
        mock_audit_service,
        mock_department,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_departments_repo.get_by_code.return_value = None
        mock_departments_repo.create.return_value = mock_department

        data = DepartmentCreate(code="CS", name="Computer Science", faculty_id=1)

        result = await service.create(data, current_user)

        assert result is not None
        mock_departments_repo.create.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_department_duplicate_code_raises(
        self, service, mock_departments_repo, mock_department
    ):
        """Test create raises when code already exists."""

        mock_departments_repo.get_by_code.return_value = mock_department

        data = DepartmentCreate(code="CS", name="CS")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_department_success(
        self,
        service,
        mock_departments_repo,
        mock_audit_service,
        mock_department,
        current_user,
    ):
        """Test update succeeds when department exists."""

        mock_departments_repo.get_by_id.return_value = mock_department
        mock_departments_repo.update_department.return_value = mock_department
        mock_departments_repo.get_director_by_department_id.return_value = None
        mock_departments_repo.count_teachers_by_department_ids.return_value = {}

        data = DepartmentUpdate(name="Updated Name")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_departments_repo.update_department.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_department_not_found(
        self, service, mock_departments_repo, current_user
    ):
        """Test update returns None when department not found."""

        mock_departments_repo.get_by_id.return_value = None

        data = DepartmentUpdate(name="Updated Name")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_department_success(
        self,
        service,
        mock_departments_repo,
        mock_audit_service,
        mock_department,
        current_user,
    ):
        """Test delete succeeds when no teachers or director."""

        mock_departments_repo.get_by_id.return_value = mock_department
        mock_departments_repo.has_active_teachers.return_value = False
        mock_departments_repo.has_active_director.return_value = False

        result = await service.delete(1, current_user)

        assert result is not None
        mock_departments_repo.delete_department.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_department_not_found(
        self, service, mock_departments_repo, current_user
    ):
        """Test delete returns None when department not found."""

        mock_departments_repo.get_by_id.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_department_with_active_teachers_raises(
        self, service, mock_departments_repo, mock_department, current_user
    ):
        """Test delete raises when department has active teachers."""

        mock_departments_repo.get_by_id.return_value = mock_department
        mock_departments_repo.has_active_teachers.return_value = True

        with pytest.raises(ValidationError):
            await service.delete(1, current_user)

    @pytest.mark.asyncio
    async def test_delete_department_with_active_director_raises(
        self, service, mock_departments_repo, mock_department, current_user
    ):
        """Test delete raises when department has active director."""

        mock_departments_repo.get_by_id.return_value = mock_department
        mock_departments_repo.has_active_teachers.return_value = False
        mock_departments_repo.has_active_director.return_value = True

        with pytest.raises(ValidationError):
            await service.delete(1, current_user)
