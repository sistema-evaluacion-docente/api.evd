"""
Tests for StatsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.stats import StatsController


class TestStatsController:
    """Test suite for StatsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock StatsService."""

        service = MagicMock()
        service.get_department_averages_by_period = AsyncMock()
        service.get_department_average_with_previous = AsyncMock()
        service.get_teacher_performance_ranking = AsyncMock()
        service.get_teacher_ranking_paginated = AsyncMock()
        service.get_grade_distribution = AsyncMock()
        service.get_teacher_average_with_previous = AsyncMock()
        service.get_teacher_history = AsyncMock()
        service.get_teacher_courses_by_period = AsyncMock()
        service.get_teacher_comments_by_subject = AsyncMock()
        service.get_teacher_dimension_averages = AsyncMock()
        service.get_teacher_vs_department = AsyncMock()
        service.get_teacher_matrix = AsyncMock()
        service.get_subjects = AsyncMock()
        service.get_subject_teachers = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return StatsController(mock_service)

    @pytest.mark.asyncio
    async def test_get_department_averages_by_period(self, controller, mock_service):
        """Test get_department_averages_by_period delegates to service."""

        mock_service.get_department_averages_by_period.return_value = [
            {"department_id": 1}
        ]

        result = await controller.get_department_averages_by_period(department_id=1)

        mock_service.get_department_averages_by_period.assert_awaited_once_with(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_department_average_with_previous(self, controller, mock_service):
        """Test get_department_average_with_previous delegates to service."""

        mock_service.get_department_average_with_previous.return_value = {
            "department_id": 1
        }

        result = await controller.get_department_average_with_previous(1, 1)

        mock_service.get_department_average_with_previous.assert_awaited_once_with(1, 1)
        assert result["department_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_performance_ranking(self, controller, mock_service):
        """Test get_teacher_performance_ranking delegates to service."""

        mock_service.get_teacher_performance_ranking.return_value = {
            "top_5": [],
            "bottom_5": [],
        }

        result = await controller.get_teacher_performance_ranking(academic_period_id=1)

        mock_service.get_teacher_performance_ranking.assert_awaited_once_with(1)
        assert "top_5" in result

    @pytest.mark.asyncio
    async def test_get_teacher_ranking_paginated(self, controller, mock_service):
        """Test get_teacher_ranking_paginated delegates to service."""

        mock_service.get_teacher_ranking_paginated.return_value = {
            "teachers": [],
            "total": 0,
        }

        result = await controller.get_teacher_ranking_paginated(
            academic_period_id=1,
            department_id=1,
            page=1,
            limit=10,
            search=None,
            sort="desc",
        )

        mock_service.get_teacher_ranking_paginated.assert_awaited_once_with(
            academic_period_id=1,
            department_id=1,
            page=1,
            limit=10,
            search=None,
            sort="desc",
        )
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_grade_distribution(self, controller, mock_service):
        """Test get_grade_distribution delegates to service."""

        mock_service.get_grade_distribution.return_value = {"bins": []}

        result = await controller.get_grade_distribution(1, 1, 0.5)

        mock_service.get_grade_distribution.assert_awaited_once_with(1, 1, 0.5)
        assert "bins" in result

    @pytest.mark.asyncio
    async def test_get_teacher_average_with_previous(self, controller, mock_service):
        """Test get_teacher_average_with_previous delegates to service."""

        mock_service.get_teacher_average_with_previous.return_value = {"teacher_id": 1}

        result = await controller.get_teacher_average_with_previous(1, 1)

        mock_service.get_teacher_average_with_previous.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_history(self, controller, mock_service):
        """Test get_teacher_history delegates to service."""

        mock_service.get_teacher_history.return_value = [{"period_code": "2024-1"}]

        result = await controller.get_teacher_history(1)

        mock_service.get_teacher_history.assert_awaited_once_with(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_teacher_courses_by_period(self, controller, mock_service):
        """Test get_teacher_courses_by_period delegates to service."""

        mock_service.get_teacher_courses_by_period.return_value = [
            {"course_code": "CS101"}
        ]

        result = await controller.get_teacher_courses_by_period(1, 1)

        mock_service.get_teacher_courses_by_period.assert_awaited_once_with(1, 1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_teacher_comments_by_subject(self, controller, mock_service):
        """Test get_teacher_comments_by_subject delegates to service."""

        mock_service.get_teacher_comments_by_subject.return_value = {"teacher_id": 1}

        result = await controller.get_teacher_comments_by_subject(1, 1)

        mock_service.get_teacher_comments_by_subject.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_dimension_averages(self, controller, mock_service):
        """Test get_teacher_dimension_averages delegates to service."""

        mock_service.get_teacher_dimension_averages.return_value = {"teacher_id": 1}

        result = await controller.get_teacher_dimension_averages(1, 1)

        mock_service.get_teacher_dimension_averages.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_vs_department(self, controller, mock_service):
        """Test get_teacher_vs_department delegates to service."""

        mock_service.get_teacher_vs_department.return_value = {"teacher_id": 1}

        result = await controller.get_teacher_vs_department(1, 1)

        mock_service.get_teacher_vs_department.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_teacher_matrix(self, controller, mock_service):
        """Test get_teacher_matrix delegates to service."""

        mock_service.get_teacher_matrix.return_value = {
            "teacher_id": 1,
            "evaluation_id": 1,
        }

        result = await controller.get_teacher_matrix(1, 1)

        mock_service.get_teacher_matrix.assert_awaited_once_with(1, 1)
        assert result["teacher_id"] == 1

    @pytest.mark.asyncio
    async def test_get_subjects(self, controller, mock_service):
        """Test get_subjects delegates to service."""

        mock_service.get_subjects.return_value = [{"course_id": 1}]

        result = await controller.get_subjects(academic_period_id=1, department_id=1)

        mock_service.get_subjects.assert_awaited_once_with(1, 1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_subject_teachers(self, controller, mock_service):
        """Test get_subject_teachers delegates to service."""

        mock_service.get_subject_teachers.return_value = {"course_id": 1}

        result = await controller.get_subject_teachers(1, 1)

        mock_service.get_subject_teachers.assert_awaited_once_with(1, 1)
        assert result["course_id"] == 1
