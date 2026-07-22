"""Tests for CourseService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.schemas.course import CourseCreate, CourseFilters, CourseUpdate
from api.services.course_service import CourseService


class TestCourseService:
    """Test suite for CourseService."""

    @pytest.fixture
    def mock_courses_repo(self):
        """Mock CoursesRepository."""

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
    def service(self, mock_courses_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return CourseService(mock_courses_repo, mock_audit_service)

    @pytest.fixture
    def mock_course(self):
        """Mock CourseModel instance with department relationship."""

        department = MagicMock(spec=DepartmentModel)
        department.id = 5
        department.code = "D01"
        department.name = "Matemáticas"

        course = MagicMock(spec=CourseModel)
        course.id = 1
        course.code = "MATH101"
        course.name = "Cálculo I"
        course.department_id = 5
        course.department = department
        course.created_at = "2024-01-01T00:00:00Z"
        course.updated_at = "2024-01-01T00:00:00Z"
        return course

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.fixture
    def create_data(self):
        """Sample CourseCreate schema."""

        return CourseCreate(
            code="MATH101",
            name="Cálculo I",
            department_id=5,
        )

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_courses(
        self, service, mock_courses_repo, mock_course
    ):
        """Test get_all returns paginated courses."""

        mock_courses_repo.search.return_value = ([mock_course], 1)

        filters = CourseFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1
        mock_courses_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_get_all_items_include_department_summary(
        self, service, mock_courses_repo, mock_course
    ):
        """Test get_all items embed department summary."""

        mock_courses_repo.search.return_value = ([mock_course], 1)

        result = await service.get_all(
            CourseFilters(), PaginationParams(page=1, limit=10)
        )

        item = result["items"][0]
        assert item["department"] == {
            "id": 5,
            "code": "D01",
            "name": "Matemáticas",
        }

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_courses_repo, mock_course):
        """Test get_by_id returns course dict when found."""

        mock_courses_repo.get_by_id.return_value = mock_course

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["code"] == "MATH101"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_courses_repo):
        """Test get_by_id returns None when not found."""

        mock_courses_repo.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_course_success(
        self,
        service,
        mock_courses_repo,
        mock_audit_service,
        mock_course,
        create_data,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_courses_repo.get_by_code.return_value = None
        mock_courses_repo.create.return_value = mock_course

        result = await service.create(create_data, current_user)

        assert result is not None
        mock_courses_repo.create.assert_called_once()
        mock_courses_repo.db.commit.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_course_duplicate_code_raises(
        self, service, mock_courses_repo, mock_course, create_data
    ):
        """Test create raises when code already exists."""

        mock_courses_repo.get_by_code.return_value = mock_course

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(create_data, {"id": 99})

        mock_courses_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_course_success(
        self,
        service,
        mock_courses_repo,
        mock_audit_service,
        mock_course,
        current_user,
    ):
        """Test update succeeds when course exists."""

        mock_courses_repo.get.return_value = mock_course
        mock_courses_repo.get_by_code.return_value = None
        mock_courses_repo.update_course.return_value = mock_course

        data = CourseUpdate(name="Cálculo II")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_courses_repo.update_course.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_course_not_found(
        self, service, mock_courses_repo, current_user
    ):
        """Test update returns None when course not found."""

        mock_courses_repo.get.return_value = None

        data = CourseUpdate(name="Cálculo II")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_course_code_change_to_duplicate_raises(
        self, service, mock_courses_repo, mock_course
    ):
        """Test update raises when new code already belongs to another course."""

        other = MagicMock(spec=CourseModel)
        other.id = 2
        mock_courses_repo.get.return_value = mock_course
        mock_courses_repo.get_by_code.return_value = other

        data = CourseUpdate(code="OTHER")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, data, {"id": 99})

        mock_courses_repo.update_course.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_course_same_code_skips_duplicate_check(
        self, service, mock_courses_repo, mock_course, current_user
    ):
        """Test update does not check duplicates when code is unchanged."""

        mock_courses_repo.get.return_value = mock_course
        mock_courses_repo.update_course.return_value = mock_course

        data = CourseUpdate(code="MATH101")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_courses_repo.get_by_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_course_success(
        self,
        service,
        mock_courses_repo,
        mock_audit_service,
        mock_course,
        current_user,
    ):
        """Test delete succeeds when the course has no academic groups."""

        mock_courses_repo.get.return_value = mock_course
        mock_courses_repo.count_academic_groups.return_value = 0
        mock_courses_repo.delete_course.return_value = mock_course

        result = await service.delete(1, current_user)

        assert result is not None
        mock_courses_repo.delete_course.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_course_not_found(
        self, service, mock_courses_repo, current_user
    ):
        """Test delete returns None when course not found."""

        mock_courses_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_course_with_academic_groups_raises(
        self, service, mock_courses_repo, mock_course
    ):
        """Test delete raises when the course has academic groups."""

        mock_courses_repo.get.return_value = mock_course
        mock_courses_repo.count_academic_groups.return_value = 3

        with pytest.raises(ValidationError):
            await service.delete(1, {"id": 99})

        mock_courses_repo.delete_course.assert_not_called()
