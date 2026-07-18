"""
Tests for FacultyService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.models.faculty import FacultyModel
from api.schemas.faculty import (
    FacultyCreate,
    FacultyFilters,
    FacultyUpdate,
)
from api.services.faculty_service import FacultyService


class TestFacultyService:
    """Test suite for FacultyService."""

    @pytest.fixture
    def mock_faculties_repo(self):
        """Mock FacultiesRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audits_repo(self):
        """Mock AuditsRepository."""

        repo = MagicMock()
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_faculties_repo, mock_users_repo, mock_audits_repo):
        """Create service instance with mocked dependencies."""

        return FacultyService(
            mock_faculties_repo,
            mock_users_repo,
            mock_audits_repo,
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
    async def test_get_by_id_found(self, service, mock_faculties_repo, mock_faculty):
        """Test get_by_id returns faculty dict when found."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.get_department_counts.return_value = {}

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["department_count"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_faculties_repo):
        """Test get_by_id returns None when not found."""

        mock_faculties_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_faculty_success(
        self, service, mock_faculties_repo, mock_audits_repo, mock_faculty, current_user
    ):
        """Test create succeeds with valid data."""

        mock_faculties_repo.get_by_code.return_value = None
        mock_faculties_repo.create_faculty.return_value = mock_faculty

        data = FacultyCreate(name="Engineering", code="ENG")

        result = await service.create(data, current_user)

        assert result is not None
        mock_faculties_repo.create_faculty.assert_called_once()
        mock_audits_repo.create.assert_called_once()

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
        self, service, mock_faculties_repo, mock_audits_repo, mock_faculty, current_user
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
        mock_audits_repo.create.assert_called_once()

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
    async def test_delete_faculty_success(
        self, service, mock_faculties_repo, mock_audits_repo, mock_faculty, current_user
    ):
        """Test delete succeeds when no departments."""

        mock_faculties_repo.get.return_value = mock_faculty
        mock_faculties_repo.has_departments.return_value = False

        result = await service.delete(1, current_user)

        assert result is not None
        mock_faculties_repo.delete_faculty.assert_called_once()
        mock_audits_repo.create.assert_called_once()

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
