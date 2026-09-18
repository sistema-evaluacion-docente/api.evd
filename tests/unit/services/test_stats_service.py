"""
Tests for StatsService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ValidationError
from api.schemas.stats import DepartmentPeriodRangeSubjectFilters
from api.services.stats_service import StatsService


class TestStatsService:
    """Test suite for StatsService."""

    @pytest.fixture
    def mock_stats_repo(self):
        """Mock StatsRepository."""

        repo = MagicMock()
        return repo

    @pytest.fixture
    def service(self, mock_stats_repo):
        """Create service instance with mocked dependencies."""

        return StatsService(mock_stats_repo)

    @pytest.fixture
    def admin_user(self):
        """Mock current user dict with an unrestricted role."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_department_averages_by_period(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_averages_by_period delegates to repository."""

        mock_stats_repo.get_department_averages_by_period = AsyncMock(
            return_value=[{"department_id": 1, "global_average": 4.5}]
        )

        result = await service.get_department_averages_by_period(1, admin_user)

        mock_stats_repo.get_department_averages_by_period.assert_awaited_once_with(
            1, None
        )
        assert result == [{"department_id": 1, "global_average": 4.5}]

    @pytest.mark.asyncio
    async def test_get_department_average_with_previous(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_average_with_previous delegates to repository."""

        mock_stats_repo.get_department_average_with_previous = AsyncMock(
            return_value={
                "department_id": 1,
                "global_average": 4.5,
                "previous_global_average": 4.2,
            }
        )

        result = await service.get_department_average_with_previous(1, 1, admin_user)

        mock_stats_repo.get_department_average_with_previous.assert_awaited_once_with(
            1, 1
        )
        assert result["global_average"] == 4.5

    @pytest.mark.asyncio
    async def test_get_department_averages_by_period_dean_without_department_id_scopes_by_faculty(
        self, service, mock_stats_repo
    ):
        """Test a DECANO with no explicit department_id gets their own
        faculty's departments combined (repository's faculty_id filter)."""

        mock_stats_repo.get_department_averages_by_period = AsyncMock(
            return_value=[{"department_id": 3, "global_average": 4.0}]
        )

        dean_user = {"id": 2, "roles": ["DECANO"], "faculty_id": 1}

        result = await service.get_department_averages_by_period(None, dean_user)

        mock_stats_repo.get_department_averages_by_period.assert_awaited_once_with(
            None, 1
        )
        assert result == [{"department_id": 3, "global_average": 4.0}]

    @pytest.mark.asyncio
    async def test_get_department_averages_by_period_dean_outside_faculty_raises_permission_denied(
        self, service, mock_stats_repo
    ):
        """Test a DECANO who explicitly asks for a department outside their
        faculty is rejected."""

        from api.exceptions import PermissionDeniedError
        from api.models.department import DepartmentModel

        other_department = MagicMock(spec=DepartmentModel)
        other_department.faculty_id = 99

        mock_stats_repo.db.query.return_value.filter.return_value.first.return_value = (
            other_department
        )
        mock_stats_repo.get_department_averages_by_period = AsyncMock()

        dean_user = {"id": 2, "roles": ["DECANO"], "faculty_id": 1}

        with pytest.raises(PermissionDeniedError):
            await service.get_department_averages_by_period(7, dean_user)

        mock_stats_repo.get_department_averages_by_period.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_faculty_averages_by_period_delegates_to_repository(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_faculty_averages_by_period delegates to repository."""

        mock_stats_repo.get_faculty_averages_by_period = AsyncMock(
            return_value=[{"faculty_id": 1, "global_average": 4.5}]
        )

        result = await service.get_faculty_averages_by_period(1, admin_user)

        mock_stats_repo.get_faculty_averages_by_period.assert_awaited_once_with(1)
        assert result == [{"faculty_id": 1, "global_average": 4.5}]

    @pytest.mark.asyncio
    async def test_get_faculty_averages_by_period_dean_outside_own_faculty_raises_permission_denied(
        self, service, mock_stats_repo
    ):
        """Test a DECANO asking for a faculty that isn't their own is rejected."""

        from api.exceptions import PermissionDeniedError

        mock_stats_repo.get_faculty_averages_by_period = AsyncMock()

        dean_user = {"id": 2, "roles": ["DECANO"], "faculty_id": 1}

        with pytest.raises(PermissionDeniedError):
            await service.get_faculty_averages_by_period(2, dean_user)

        mock_stats_repo.get_faculty_averages_by_period.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_teacher_performance_ranking(self, service, mock_stats_repo):
        """Test get_teacher_performance_ranking delegates to repository."""

        mock_stats_repo.get_teacher_performance_ranking = AsyncMock(
            return_value={
                "top_5": [],
                "bottom_5": [],
            }
        )

        result = await service.get_teacher_performance_ranking(academic_period_id=1)

        mock_stats_repo.get_teacher_performance_ranking.assert_awaited_once_with(1)
        assert "top_5" in result

    @pytest.mark.asyncio
    async def test_get_teacher_ranking_paginated(self, service, mock_stats_repo):
        """Test get_teacher_ranking_paginated delegates to repository."""

        mock_stats_repo.get_teacher_ranking_paginated = AsyncMock(
            return_value={
                "teachers": [],
                "total": 0,
                "page": 1,
                "limit": 10,
                "pages": 0,
            }
        )

        result = await service.get_teacher_ranking_paginated(
            academic_period_id=1,
            department_id=1,
            page=1,
            limit=10,
            search=None,
            sort="desc",
        )

        mock_stats_repo.get_teacher_ranking_paginated.assert_awaited_once_with(
            academic_period_id=1,
            department_id=1,
            page=1,
            limit=10,
            search=None,
            sort="desc",
        )
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_grade_distribution(self, service, mock_stats_repo):
        """Test get_grade_distribution delegates to repository."""

        mock_stats_repo.get_grade_distribution = AsyncMock(
            return_value={
                "bins": [],
            }
        )

        result = await service.get_grade_distribution(
            academic_period_id=1, department_id=1, bin_size=0.5
        )

        mock_stats_repo.get_grade_distribution.assert_awaited_once_with(1, 1, 0.5)
        assert "bins" in result

    @pytest.mark.asyncio
    async def test_get_teacher_average_with_previous(self, service, mock_stats_repo):
        """Test get_teacher_average_with_previous delegates to repository."""

        mock_stats_repo.get_teacher_average_with_previous = AsyncMock(
            return_value={
                "teacher_id": 1,
                "overall_average": 4.5,
            }
        )

        result = await service.get_teacher_average_with_previous(1, 1)

        mock_stats_repo.get_teacher_average_with_previous.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_history(self, service, mock_stats_repo):
        """Test get_teacher_history delegates to repository."""

        mock_stats_repo.get_teacher_history = AsyncMock(
            return_value=[{"period_code": "2024-1", "overall_average": 4.5}]
        )

        result = await service.get_teacher_history(1)

        mock_stats_repo.get_teacher_history.assert_awaited_once_with(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_teacher_courses_by_period(self, service, mock_stats_repo):
        """Test get_teacher_courses_by_period delegates to repository."""

        mock_stats_repo.get_teacher_courses_by_period = AsyncMock(
            return_value=[{"course_code": "CS101", "overall_average": 4.5}]
        )

        result = await service.get_teacher_courses_by_period(1, 1)

        mock_stats_repo.get_teacher_courses_by_period.assert_awaited_once_with(1, 1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_teacher_comments_by_subject(self, service, mock_stats_repo):
        """Test get_teacher_comments_by_subject delegates to repository."""

        mock_stats_repo.get_teacher_comments_by_subject = AsyncMock(
            return_value={
                "teacher_id": 1,
                "subjects": [],
            }
        )

        result = await service.get_teacher_comments_by_subject(1, 1)

        mock_stats_repo.get_teacher_comments_by_subject.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_dimension_averages(self, service, mock_stats_repo):
        """Test get_teacher_dimension_averages delegates to repository."""

        mock_stats_repo.get_teacher_dimension_averages = AsyncMock(
            return_value={
                "teacher_id": 1,
                "dimensions": [],
            }
        )

        result = await service.get_teacher_dimension_averages(1, 1)

        mock_stats_repo.get_teacher_dimension_averages.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_vs_department(self, service, mock_stats_repo):
        """Test get_teacher_vs_department delegates to repository."""

        mock_stats_repo.get_teacher_vs_department = AsyncMock(
            return_value={
                "teacher_id": 1,
                "department_id": 1,
            }
        )

        result = await service.get_teacher_vs_department(1, 1)

        mock_stats_repo.get_teacher_vs_department.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_vs_previous_period(self, service, mock_stats_repo):
        """Test get_teacher_vs_previous_period delegates to repository."""

        mock_stats_repo.get_teacher_vs_previous_period = AsyncMock(
            return_value={
                "teacher_id": 1,
                "academic_period_id": 2,
                "previous_academic_period_id": 1,
                "current_overall_average": 4.5,
                "previous_overall_average": 4.2,
            }
        )

        result = await service.get_teacher_vs_previous_period(1, 2)

        mock_stats_repo.get_teacher_vs_previous_period.assert_awaited_once_with(1, 2)
        assert result["teacher_id"] == 1
        assert result["current_overall_average"] == 4.5
        assert result["previous_overall_average"] == 4.2

    @pytest.mark.asyncio
    async def test_get_teacher_matrix(self, service, mock_stats_repo):
        """Test get_teacher_matrix delegates to repository."""

        mock_stats_repo.get_teacher_matrix = AsyncMock(
            return_value={
                "teacher_id": 1,
                "evaluation_id": 1,
                "courses": [],
            }
        )

        result = await service.get_teacher_matrix(1, 1)

        mock_stats_repo.get_teacher_matrix.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_subjects(self, service, mock_stats_repo):
        """Test get_subjects delegates to repository."""

        mock_stats_repo.get_subjects = AsyncMock(
            return_value=[{"course_id": 1, "overall_average": 4.5}]
        )

        result = await service.get_subjects(academic_period_id=1, department_id=1)

        mock_stats_repo.get_subjects.assert_awaited_once_with(1, 1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_subject_teachers(self, service, mock_stats_repo):
        """Test get_subject_teachers delegates to repository."""

        mock_stats_repo.get_subject_teachers = AsyncMock(
            return_value={
                "course_id": 1,
                "teachers": [],
            }
        )

        result = await service.get_subject_teachers(1, 1)

        mock_stats_repo.get_subject_teachers.assert_awaited_once_with(1, 1)
        assert result["course_id"] == 1

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_with_valid_range_delegates_to_repository(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_period_range_report delegates to repository when
        the period codes are well-formed and in order."""

        mock_stats_repo.get_department_period_range_report = AsyncMock(
            return_value={
                "department_id": 1,
                "dimensions": [],
            }
        )

        result = await service.get_department_period_range_report(
            1, "2020-1", "2022-1", admin_user
        )

        mock_stats_repo.get_department_period_range_report.assert_awaited_once_with(
            1, "2020-1", "2022-1"
        )
        assert result["department_id"] == 1

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_with_malformed_code_raises_validation_error(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_period_range_report rejects period codes that
        don't match the 'AAAA-N' format."""

        mock_stats_repo.get_department_period_range_report = AsyncMock()

        with pytest.raises(ValidationError):
            await service.get_department_period_range_report(
                1, "2020-I", "2022-1", admin_user
            )

        mock_stats_repo.get_department_period_range_report.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_with_inverted_range_raises_validation_error(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_period_range_report rejects a start period
        that is after the end period."""

        mock_stats_repo.get_department_period_range_report = AsyncMock()

        with pytest.raises(ValidationError):
            await service.get_department_period_range_report(
                1, "2022-1", "2020-1", admin_user
            )

        mock_stats_repo.get_department_period_range_report.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_without_department_id_raises_validation_error(
        self, service, mock_stats_repo, admin_user
    ):
        """Test get_department_period_range_report rejects a missing
        department_id when current_user has none to fall back on either."""

        mock_stats_repo.get_department_period_range_report = AsyncMock()

        with pytest.raises(ValidationError):
            await service.get_department_period_range_report(
                None, "2020-1", "2022-1", admin_user
            )

        mock_stats_repo.get_department_period_range_report.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_director_defaults_to_own_department(
        self, service, mock_stats_repo
    ):
        """Test a DIRECTOR without an explicit department_id falls back to
        their own department, resolved from current_user."""

        mock_stats_repo.get_department_period_range_report = AsyncMock(
            return_value={"department_id": 5, "dimensions": []}
        )

        director_user = {
            "id": 1,
            "roles": ["DIRECTOR DE DEPARTAMENTO"],
            "department_id": 5,
        }

        result = await service.get_department_period_range_report(
            None, "2020-1", "2022-1", director_user
        )

        mock_stats_repo.get_department_period_range_report.assert_awaited_once_with(
            5, "2020-1", "2022-1"
        )
        assert result["department_id"] == 5

    @pytest.mark.asyncio
    async def test_get_department_period_range_report_dean_outside_faculty_raises_permission_denied(
        self, service, mock_stats_repo
    ):
        """Test a DECANO asking for a department outside their faculty is
        rejected before the repository query runs."""

        from api.exceptions import PermissionDeniedError
        from api.models.department import DepartmentModel

        other_department = MagicMock(spec=DepartmentModel)
        other_department.faculty_id = 99

        mock_stats_repo.db.query.return_value.filter.return_value.first.return_value = (
            other_department
        )
        mock_stats_repo.get_department_period_range_report = AsyncMock()

        dean_user = {"id": 2, "roles": ["DECANO"], "faculty_id": 1}

        with pytest.raises(PermissionDeniedError):
            await service.get_department_period_range_report(
                7, "2020-1", "2022-1", dean_user
            )

        mock_stats_repo.get_department_period_range_report.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_department_period_range_subjects_with_valid_range_returns_paginated_response(
        self, service, mock_stats_repo
    ):
        """Test get_department_period_range_subjects builds a paginated
        response from the repository's (items, total) tuple when the
        period codes are well-formed and in order."""

        mock_stats_repo.get_department_period_range_subjects = AsyncMock(
            return_value=(
                [
                    {
                        "course_name": "Cálculo I",
                        "course_codes": ["MAT101"],
                        "overall_average": 4.5,
                        "groups": [{"academic_group_id": 1, "group_name": "A"}],
                    }
                ],
                1,
            )
        )

        filters = DepartmentPeriodRangeSubjectFilters(
            start_period_code="2020-1", end_period_code="2022-1"
        )
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_department_period_range_subjects(
            1, filters, pagination
        )

        mock_stats_repo.get_department_period_range_subjects.assert_awaited_once_with(
            1, filters, pagination
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_department_period_range_subjects_with_missing_department_returns_none(
        self, service, mock_stats_repo
    ):
        """Test get_department_period_range_subjects returns None when the
        repository can't find the department."""

        mock_stats_repo.get_department_period_range_subjects = AsyncMock(
            return_value=None
        )

        filters = DepartmentPeriodRangeSubjectFilters(
            start_period_code="2020-1", end_period_code="2022-1"
        )
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_department_period_range_subjects(
            1, filters, pagination
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_department_period_range_subjects_with_malformed_code_raises_validation_error(
        self, service, mock_stats_repo
    ):
        """Test get_department_period_range_subjects rejects period codes
        that don't match the 'AAAA-N' format."""

        mock_stats_repo.get_department_period_range_subjects = AsyncMock()

        filters = DepartmentPeriodRangeSubjectFilters(
            start_period_code="2020-I", end_period_code="2022-1"
        )
        pagination = PaginationParams(page=1, limit=10)

        with pytest.raises(ValidationError):
            await service.get_department_period_range_subjects(1, filters, pagination)

        mock_stats_repo.get_department_period_range_subjects.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_department_period_range_subjects_with_inverted_range_raises_validation_error(
        self, service, mock_stats_repo
    ):
        """Test get_department_period_range_subjects rejects a start period
        that is after the end period."""

        mock_stats_repo.get_department_period_range_subjects = AsyncMock()

        filters = DepartmentPeriodRangeSubjectFilters(
            start_period_code="2022-1", end_period_code="2020-1"
        )
        pagination = PaginationParams(page=1, limit=10)

        with pytest.raises(ValidationError):
            await service.get_department_period_range_subjects(1, filters, pagination)

        mock_stats_repo.get_department_period_range_subjects.assert_not_awaited()
