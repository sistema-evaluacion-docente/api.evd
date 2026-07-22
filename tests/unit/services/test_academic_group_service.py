"""Tests for AcademicGroupService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.course import CourseModel
from api.models.teacher import TeacherModel
from api.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupFilters,
    AcademicGroupUpdate,
)
from api.services.academic_group_service import AcademicGroupService


class TestAcademicGroupService:
    """Test suite for AcademicGroupService."""

    @pytest.fixture
    def mock_groups_repo(self):
        """Mock AcademicGroupsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_groups_repo, mock_periods_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return AcademicGroupService(
            mock_groups_repo,
            mock_periods_repo,
            mock_audit_service,
        )

    @pytest.fixture
    def mock_period(self):
        """Mock active AcademicPeriodModel instance."""

        period = MagicMock(spec=AcademicPeriodModel)
        period.id = 1
        period.code = "2024-1"
        period.name = "Primer semestre 2024"
        period.active = True
        return period

    @pytest.fixture
    def mock_group(self, mock_period):
        """Mock AcademicGroupModel instance with relationships."""

        course = MagicMock(spec=CourseModel)
        course.id = 10
        course.code = "MATH101"
        course.name = "Cálculo I"
        course.department_id = 5

        teacher = MagicMock(spec=TeacherModel)
        teacher.id = 20
        teacher.user = MagicMock()
        teacher.user.institutional_code = "12345"
        teacher.user.name = None

        group = MagicMock(spec=AcademicGroupModel)
        group.id = 1
        group.course_id = 10
        group.teacher_id = 20
        group.academic_period_id = 1
        group.group_name = "A"
        group.course = course
        group.teacher = teacher
        group.academic_period = mock_period
        group.created_at = "2024-01-01T00:00:00Z"
        group.updated_at = "2024-01-01T00:00:00Z"
        return group

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.fixture
    def create_data(self):
        """Sample AcademicGroupCreate schema."""

        return AcademicGroupCreate(
            course_id=10,
            teacher_id=20,
            academic_period_id=1,
            group_name="A",
        )

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_groups(
        self, service, mock_groups_repo, mock_group
    ):
        """Test get_all returns paginated academic groups."""

        mock_groups_repo.search.return_value = ([mock_group], 1)

        filters = AcademicGroupFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1
        mock_groups_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_get_all_items_include_related_entities(
        self, service, mock_groups_repo, mock_group
    ):
        """Test get_all items embed course, teacher and period summaries."""

        mock_groups_repo.search.return_value = ([mock_group], 1)

        result = await service.get_all(
            AcademicGroupFilters(), PaginationParams(page=1, limit=10)
        )

        item = result["items"][0]
        assert item["course"] == {
            "id": 10,
            "code": "MATH101",
            "name": "Cálculo I",
            "department_id": 5,
        }
        assert item["teacher"] == {
            "id": 20,
            "institutional_code": "12345",
            "name": None,
        }
        assert item["academic_period"] == {
            "id": 1,
            "code": "2024-1",
            "name": "Primer semestre 2024",
            "active": True,
        }

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_groups_repo, mock_group):
        """Test get_by_id returns group dict when found."""

        mock_groups_repo.get_by_id.return_value = mock_group

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["group_name"] == "A"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_groups_repo):
        """Test get_by_id returns None when not found."""

        mock_groups_repo.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_group_success(
        self,
        service,
        mock_groups_repo,
        mock_periods_repo,
        mock_audit_service,
        mock_group,
        mock_period,
        create_data,
        current_user,
    ):
        """Test create succeeds with valid data and active period."""

        mock_periods_repo.get.return_value = mock_period
        mock_groups_repo.get_by_course_teacher_period_name.return_value = None
        mock_groups_repo.create.return_value = mock_group

        result = await service.create(create_data, current_user)

        assert result is not None
        mock_groups_repo.create.assert_called_once()
        mock_groups_repo.db.commit.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_group_duplicate_raises(
        self,
        service,
        mock_groups_repo,
        mock_periods_repo,
        mock_group,
        mock_period,
        create_data,
    ):
        """Test create raises when the same combination already exists."""

        mock_periods_repo.get.return_value = mock_period
        mock_groups_repo.get_by_course_teacher_period_name.return_value = mock_group

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(create_data, {"id": 99})

        mock_groups_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_group_inactive_period_raises(
        self, service, mock_groups_repo, mock_periods_repo, mock_period, create_data
    ):
        """Test create raises when the academic period is not active."""

        mock_period.active = False
        mock_periods_repo.get.return_value = mock_period

        with pytest.raises(ValidationError):
            await service.create(create_data, {"id": 99})

        mock_groups_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_group_missing_period_raises(
        self, service, mock_groups_repo, mock_periods_repo, create_data
    ):
        """Test create raises when the academic period does not exist."""

        mock_periods_repo.get.return_value = None

        with pytest.raises(ValidationError):
            await service.create(create_data, {"id": 99})

        mock_groups_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_group_success(
        self,
        service,
        mock_groups_repo,
        mock_audit_service,
        mock_group,
        current_user,
    ):
        """Test update succeeds when group exists and period is unchanged."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.get_by_course_teacher_period_name.return_value = None
        mock_groups_repo.update_group.return_value = mock_group

        data = AcademicGroupUpdate(group_name="B")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_groups_repo.update_group.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_group_not_found(
        self, service, mock_groups_repo, current_user
    ):
        """Test update returns None when group not found."""

        mock_groups_repo.get.return_value = None

        data = AcademicGroupUpdate(group_name="B")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_group_period_change_to_active_succeeds(
        self,
        service,
        mock_groups_repo,
        mock_periods_repo,
        mock_group,
        mock_period,
        current_user,
    ):
        """Test update re-validates period only when academic_period_id changes."""

        mock_period.id = 2
        mock_periods_repo.get.return_value = mock_period
        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.get_by_course_teacher_period_name.return_value = None
        mock_groups_repo.update_group.return_value = mock_group

        data = AcademicGroupUpdate(academic_period_id=2)

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_periods_repo.get.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_update_group_period_change_to_inactive_raises(
        self,
        service,
        mock_groups_repo,
        mock_periods_repo,
        mock_group,
        mock_period,
    ):
        """Test update raises when moving the group to an inactive period."""

        mock_period.active = False
        mock_periods_repo.get.return_value = mock_period
        mock_groups_repo.get.return_value = mock_group

        data = AcademicGroupUpdate(academic_period_id=2)

        with pytest.raises(ValidationError):
            await service.update(1, data, {"id": 99})

        mock_groups_repo.update_group.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_group_same_period_skips_period_validation(
        self, service, mock_groups_repo, mock_periods_repo, mock_group, current_user
    ):
        """Test update does not query the period when academic_period_id is unchanged."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.get_by_course_teacher_period_name.return_value = None
        mock_groups_repo.update_group.return_value = mock_group

        data = AcademicGroupUpdate(academic_period_id=1)

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_periods_repo.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_group_duplicate_combination_raises(
        self, service, mock_groups_repo, mock_group
    ):
        """Test update raises when the new combination already exists."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.get_by_course_teacher_period_name.return_value = mock_group

        data = AcademicGroupUpdate(group_name="B")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, data, {"id": 99})

        mock_groups_repo.update_group.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_group_success(
        self,
        service,
        mock_groups_repo,
        mock_audit_service,
        mock_group,
        current_user,
    ):
        """Test delete succeeds when the group has no dependencies."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.count_evaluation_scores.return_value = 0
        mock_groups_repo.count_comments.return_value = 0
        mock_groups_repo.delete_group.return_value = mock_group

        result = await service.delete(1, current_user)

        assert result is not None
        mock_groups_repo.delete_group.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_group_not_found(
        self, service, mock_groups_repo, current_user
    ):
        """Test delete returns None when group not found."""

        mock_groups_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_group_with_evaluation_scores_raises(
        self, service, mock_groups_repo, mock_group
    ):
        """Test delete raises when the group has evaluation scores."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.count_evaluation_scores.return_value = 3
        mock_groups_repo.count_comments.return_value = 0

        with pytest.raises(ValidationError):
            await service.delete(1, {"id": 99})

        mock_groups_repo.delete_group.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_group_with_comments_raises(
        self, service, mock_groups_repo, mock_group
    ):
        """Test delete raises when the group has comments."""

        mock_groups_repo.get.return_value = mock_group
        mock_groups_repo.count_evaluation_scores.return_value = 0
        mock_groups_repo.count_comments.return_value = 2

        with pytest.raises(ValidationError):
            await service.delete(1, {"id": 99})

        mock_groups_repo.delete_group.assert_not_called()
