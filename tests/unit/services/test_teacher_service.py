"""
Tests for TeacherService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError
from api.models.teacher import TeacherModel
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)
from api.services.teacher_service import TeacherService


class TestTeacherService:
    """Test suite for TeacherService."""

    @pytest.fixture
    def mock_teachers_repo(self):
        """Mock TeachersRepository."""

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
    def mock_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.get_previous_period_code = AsyncMock()
        repo.get_by_code = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_service(self):
        """Mock UserService."""

        service = MagicMock()
        service.create_user_with_roles = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_teachers_repo,
        mock_users_repo,
        mock_audit_service,
        mock_periods_repo,
        mock_user_service,
    ):
        """Create service instance with mocked dependencies."""

        return TeacherService(
            mock_teachers_repo,
            mock_users_repo,
            mock_audit_service,
            mock_periods_repo,
            mock_user_service,
        )

    @pytest.fixture
    def mock_teacher(self):
        """Mock TeacherModel instance."""

        teacher = MagicMock(spec=TeacherModel)
        teacher.id = 1
        teacher.institutional_code = "12345"
        teacher.department_id = 1
        teacher.contract_type = "FULL_TIME"
        teacher.user_id = 1
        teacher.active = True
        teacher.user = None
        teacher.created_at = "2024-01-01T00:00:00Z"
        teacher.updated_at = "2024-01-01T00:00:00Z"
        return teacher

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_teachers(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test get_all returns paginated teachers."""

        mock_teachers_repo.search.return_value = ([mock_teacher], 1)
        mock_teachers_repo.get_user_role_names = MagicMock(return_value=["DOCENTE"])

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_averages(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test get_all_with_averages includes overall_average."""

        mock_teachers_repo.search.return_value = ([mock_teacher], 1)
        mock_teachers_repo.get_teacher_averages_by_period.return_value = {1: 4.5}

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all_with_averages(filters, pagination, 1)

        assert result["items"][0]["overall_average"] == 4.5

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_teachers_repo, mock_teacher):
        """Test get_by_id returns teacher dict when found."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_teachers_repo):
        """Test get_by_id returns None when not found."""

        mock_teachers_repo.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_teachers_repo.get_by_institutional_code.return_value = None
        mock_teachers_repo.create.return_value = mock_teacher

        data = TeacherCreate(
            institutional_code="12345",
            department_id=1,
            contract_type="FULL_TIME",
        )

        result = await service.create(data, current_user)

        assert result is not None
        mock_teachers_repo.create.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_teacher_duplicate_code_raises(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test create raises when institutional_code already exists."""

        mock_teachers_repo.get_by_institutional_code.return_value = mock_teacher

        data = TeacherCreate(institutional_code="12345")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_create_with_user_success(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_user_service,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test create_with_user creates user and teacher."""

        mock_teachers_repo.get_by_institutional_code.side_effect = [None, mock_teacher]
        mock_users_repo.get_by_email.return_value = None

        data = TeacherCreateWithUser(
            email="test@example.com",
            name="Test Teacher",
            institutional_code="12345",
        )

        result = await service.create_with_user(data, current_user)

        assert result is not None
        mock_user_service.create_user_with_roles.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_user_duplicate_code_raises(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test create_with_user raises when institutional_code exists."""

        mock_teachers_repo.get_by_institutional_code.return_value = mock_teacher

        data = TeacherCreateWithUser(
            email="test@example.com",
            name="Test",
            institutional_code="12345",
        )

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create_with_user(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test update succeeds when teacher exists."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_teachers_repo.update_teacher.return_value = mock_teacher

        data = TeacherUpdate(contract_type="PART_TIME")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_teachers_repo.update_teacher.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_teacher_not_found(
        self, service, mock_teachers_repo, current_user
    ):
        """Test update returns None when teacher not found."""

        mock_teachers_repo.get_by_id.return_value = None

        data = TeacherUpdate(contract_type="PART_TIME")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test delete succeeds when teacher exists."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher

        result = await service.delete(1, current_user)

        assert result is not None
        mock_teachers_repo.delete_teacher.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_teacher_not_found(
        self, service, mock_teachers_repo, current_user
    ):
        """Test delete returns None when teacher not found."""

        mock_teachers_repo.get_by_id.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_department(
        self, service, mock_teachers_repo, mock_periods_repo
    ):
        """Test count_by_department delegates to repository."""

        mock_periods_repo.get_by_id.return_value = {"code": "2025-1"}
        mock_periods_repo.get_previous_period_code.return_value = "2024-2"
        mock_periods_repo.get_by_code.return_value = MagicMock(id=2)
        mock_teachers_repo.count_by_department.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await service.count_by_department(1, 1)

        assert result["current_count"] == 10
        assert result["previous_count"] == 8

    @pytest.mark.asyncio
    async def test_get_history(self, service, mock_teachers_repo):
        """Test get_history delegates to repository."""

        expected = {
            "teacher_id": 1,
            "institutional_code": "12345",
            "history": [],
        }
        mock_teachers_repo.get_history.return_value = expected

        result = await service.get_history(1)

        assert result == expected
        mock_teachers_repo.get_history.assert_called_once_with(1)
