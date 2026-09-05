"""Tests for ComparisonController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.comparison import ComparisonController


class TestComparisonController:
    """Test suite for ComparisonController."""

    @pytest.fixture
    def mock_repository(self):
        """Mock ComparisonRepository."""

        repo = MagicMock()
        repo.get_teacher_info = AsyncMock()
        repo.get_period = AsyncMock()
        repo.get_overall_stats = AsyncMock()
        repo.get_question_averages = AsyncMock()
        repo.get_courses = AsyncMock()
        repo.get_comments_by_risk = AsyncMock()
        return repo

    @pytest.fixture
    def controller(self, mock_repository):
        """Create controller instance with mocked repository."""

        return ComparisonController(mock_repository)

    @pytest.mark.asyncio
    async def test_returns_none_when_teacher_not_found(
        self, controller, mock_repository
    ):
        """Test the comparison bails out early when the teacher does not exist."""

        mock_repository.get_teacher_info.return_value = None

        result = await controller.compare_teachers_semesters(999, 2, 1)

        assert result is None
        mock_repository.get_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_a_period_is_missing(
        self, controller, mock_repository
    ):
        """Test the comparison bails out when either period does not exist."""

        mock_repository.get_teacher_info.return_value = {
            "teacher_id": 1, "teacher_name": "Ana"
        }
        mock_repository.get_period.side_effect = [None, MagicMock()]

        result = await controller.compare_teachers_semesters(1, 2, 1)

        assert result is None
        mock_repository.get_overall_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_teacher_has_no_groups_in_current_semester(
        self, controller, mock_repository
    ):
        """Test the comparison bails out when there is no data for the semester."""

        mock_repository.get_teacher_info.return_value = {
            "teacher_id": 1, "teacher_name": "Ana"
        }
        mock_repository.get_period.side_effect = [
            MagicMock(code="2026-1"), MagicMock(code="2025-2")
        ]
        mock_repository.get_overall_stats.return_value = {
            "overall_average": None, "group_count": 0, "respondent_count": 0
        }

        result = await controller.compare_teachers_semesters(1, 2, 1)

        assert result is None
        mock_repository.get_question_averages.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_the_full_comparison(self, controller, mock_repository):
        """Test the full comparison, exercising every dimension/comment branch."""

        mock_repository.get_teacher_info.return_value = {
            "teacher_id": 1, "teacher_name": "Ana"
        }
        current_period = MagicMock(code="2026-1")
        old_period = MagicMock(code="2025-2")
        mock_repository.get_period.side_effect = [current_period, old_period]
        mock_repository.get_overall_stats.side_effect = [
            {"overall_average": 4.5, "group_count": 2, "respondent_count": 30},
            {"overall_average": 4.0, "group_count": 1, "respondent_count": 15},
        ]
        mock_repository.get_question_averages.side_effect = [
            {"001": 4.5, "002": 4.0},
            {"001": 4.0},
        ]
        mock_repository.get_courses.side_effect = [
            [{"course_code": "BD101", "overall_average": 4.5}],
            [{"course_code": "BD101", "overall_average": 4.0}],
        ]
        mock_repository.get_comments_by_risk.side_effect = [
            {"total_comments": 3, "risk_breakdown": {"ALTO": 1}},
            None,
        ]

        result = await controller.compare_teachers_semesters(1, 2, 1)

        assert result["teacher_id"] == 1
        assert result["current_semester"] == "2026-1"
        assert result["old_semester"] == "2025-2"
        assert result["average_difference"] == 0.5
        assert result["current_courses"][0]["semester"] == "2026-1"
        assert result["current_comments"]["semester"] == "2026-1"
        assert result["old_comments"] is None
        assert result["current_weakest_dimension"] is not None
        assert result["current_strongest_dimension"] is not None
        # A dimension with no data in either semester (e.g. "Integración
        # Interpersonal") reports None averages and is skipped by min/max.
        assert any(
            d["current_average"] is None for d in result["dimensions"]
        )

    @pytest.mark.asyncio
    async def test_average_difference_is_none_without_both_averages(
        self, controller, mock_repository
    ):
        """Test average_difference stays None when one side has no average."""

        mock_repository.get_teacher_info.return_value = {
            "teacher_id": 1, "teacher_name": "Ana"
        }
        mock_repository.get_period.side_effect = [
            MagicMock(code="2026-1"), MagicMock(code="2025-2")
        ]
        mock_repository.get_overall_stats.side_effect = [
            {"overall_average": None, "group_count": 1, "respondent_count": 5},
            {"overall_average": 4.0, "group_count": 1, "respondent_count": 5},
        ]
        mock_repository.get_question_averages.side_effect = [{}, {}]
        mock_repository.get_courses.side_effect = [[], []]
        mock_repository.get_comments_by_risk.side_effect = [None, None]

        result = await controller.compare_teachers_semesters(1, 2, 1)

        assert result["average_difference"] is None
        assert result["current_weakest_dimension"] is None
        assert result["current_strongest_dimension"] is None
