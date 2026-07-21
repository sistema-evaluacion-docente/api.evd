"""
Tests for StatsService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

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

    @pytest.mark.asyncio
    async def test_get_department_averages_by_period(self, service, mock_stats_repo):
        """Test get_department_averages_by_period delegates to repository."""

        mock_stats_repo.get_department_averages_by_period = AsyncMock(
            return_value=[{"department_id": 1, "global_average": 4.5}]
        )

        result = await service.get_department_averages_by_period(department_id=1)

        mock_stats_repo.get_department_averages_by_period.assert_awaited_once_with(1)
        assert result == [{"department_id": 1, "global_average": 4.5}]

    @pytest.mark.asyncio
    async def test_get_department_average_with_previous(self, service, mock_stats_repo):
        """Test get_department_average_with_previous delegates to repository."""

        mock_stats_repo.get_department_average_with_previous = AsyncMock(
            return_value={
                "department_id": 1,
                "global_average": 4.5,
                "previous_global_average": 4.2,
            }
        )

        result = await service.get_department_average_with_previous(1, 1)

        mock_stats_repo.get_department_average_with_previous.assert_awaited_once_with(
            1, 1
        )
        assert result["global_average"] == 4.5

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
