"""Tests for DashboardService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.dashboard_service import DashboardService


class TestDashboardService:
    """Test suite for DashboardService."""

    @pytest.fixture
    def mock_evaluations_repo(self):
        """Mock EvaluationsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_stats_repo(self):
        """Mock StatsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        return MagicMock()

    @pytest.fixture
    def service(self, mock_evaluations_repo, mock_stats_repo, mock_periods_repo):
        """Create service instance with mocked dependencies."""

        return DashboardService(
            mock_evaluations_repo, mock_stats_repo, mock_periods_repo
        )

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_none_when_period_not_found(
        self, service, mock_periods_repo
    ):
        """Test get_dashboard returns None when period_name does not match any period."""

        mock_periods_repo.get_by_name.return_value = None

        result = await service.get_dashboard(
            teacher_id=1, period_name="Nonexistent", department_id=1
        )

        assert result is None
        mock_periods_repo.get_by_name.assert_called_once_with("Nonexistent")

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_none_when_no_evaluation_for_period(
        self, service, mock_periods_repo, mock_evaluations_repo
    ):
        """Test get_dashboard returns None when no evaluation exists for the period and department."""

        mock_period = MagicMock()
        mock_period.id = 10
        mock_periods_repo.get_by_name.return_value = mock_period
        mock_evaluations_repo.get_by_period_and_department.return_value = None

        result = await service.get_dashboard(
            teacher_id=1, period_name="2024-1", department_id=5
        )

        assert result is None
        mock_evaluations_repo.get_by_period_and_department.assert_called_once_with(
            10, 5
        )

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_none_when_teacher_detail_not_found(
        self, service, mock_periods_repo, mock_evaluations_repo
    ):
        """Test get_dashboard returns None when teacher detail is not found."""

        mock_period = MagicMock()
        mock_period.id = 10
        mock_periods_repo.get_by_name.return_value = mock_period
        mock_evaluations_repo.get_by_period_and_department.return_value = {"id": 5}
        mock_evaluations_repo.get_teacher_detail.return_value = None

        result = await service.get_dashboard(
            teacher_id=99, period_name="2024-1", department_id=5
        )

        assert result is None
        mock_evaluations_repo.get_teacher_detail.assert_called_once_with(5, 99)

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_combined_data(
        self, service, mock_periods_repo, mock_evaluations_repo, mock_stats_repo
    ):
        """Test get_dashboard returns combined data when all lookups succeed."""

        mock_period = MagicMock()
        mock_period.id = 10
        mock_periods_repo.get_by_name.return_value = mock_period
        mock_evaluations_repo.get_by_period_and_department.return_value = {"id": 5}

        mock_detail = {"teacher_id": 1, "evaluation_id": 5, "overall_average": 4.5}
        mock_evaluations_repo.get_teacher_detail.return_value = mock_detail

        mock_comparison = {"dimensions": []}
        mock_stats_repo.get_teacher_vs_previous_period = AsyncMock(
            return_value=mock_comparison
        )

        mock_comments = {"teacher_id": 1, "evaluation_id": 5, "courses": []}
        mock_evaluations_repo.get_teacher_comments.return_value = mock_comments

        mock_matrix = {"courses": []}
        mock_stats_repo.get_teacher_matrix = AsyncMock(return_value=mock_matrix)

        result = await service.get_dashboard(
            teacher_id=1, period_name="2024-1", department_id=5
        )

        assert result is not None
        assert result["evaluation_detail"] == mock_detail
        assert result["period_comparison"] == mock_comparison
        assert result["comments"] == mock_comments
        assert result["matrix"] == mock_matrix

        mock_periods_repo.get_by_name.assert_called_once_with("2024-1")
        mock_evaluations_repo.get_by_period_and_department.assert_called_once_with(
            10, 5
        )
        mock_evaluations_repo.get_teacher_detail.assert_called_once_with(5, 1)
        mock_stats_repo.get_teacher_vs_previous_period.assert_awaited_once_with(1, 10)
        mock_evaluations_repo.get_teacher_comments.assert_called_once_with(5, 1)
        mock_stats_repo.get_teacher_matrix.assert_awaited_once_with(1, 5)
