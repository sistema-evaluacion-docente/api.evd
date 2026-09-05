"""Tests for AdminDashboardController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.admin_dashboard import AdminDashboardController


class TestAdminDashboardController:
    """Test suite for AdminDashboardController."""

    @pytest.fixture
    def mock_repository(self):
        """Mock AdminDashboardRepository."""

        repo = MagicMock()
        repo.get_counts = AsyncMock(return_value={"users": 10})
        repo.get_recent_audits_with_users = AsyncMock(return_value=[{"id": 1}])
        repo.get_periods = AsyncMock(return_value=[{"id": 1}])
        return repo

    @pytest.fixture
    def controller(self, mock_repository):
        """Create controller instance with mocked repository."""

        return AdminDashboardController(mock_repository)

    @pytest.mark.asyncio
    async def test_get_dashboard_aggregates_the_three_queries(
        self, controller, mock_repository
    ):
        """Test get_dashboard combines counts, audits and periods."""

        result = await controller.get_dashboard()

        assert result == {
            "counts": {"users": 10},
            "recent_audits": [{"id": 1}],
            "periods": [{"id": 1}],
        }
        mock_repository.get_recent_audits_with_users.assert_awaited_once_with(
            limit=10
        )
