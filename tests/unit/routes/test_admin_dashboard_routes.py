"""Tests for the admin dashboard route.

What the route layer owns here: the ADMIN-only guard and wrapping the
controller's dict in the manual ``ResponseSchema`` envelope.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.admin_dashboard import get_admin_dashboard_controller
from api.routes.admin_dashboard import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER

DASHBOARD = {"total_users": 10, "total_evaluations": 5, "recent_audits": []}


@pytest.fixture
def controller():
    """Mock AdminDashboardController."""

    mock = MagicMock()
    mock.get_dashboard = AsyncMock(return_value=DASHBOARD)
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the admin dashboard router."""

    return make_client(router, {get_admin_dashboard_controller: controller})


class TestGetAdminDashboard:
    """GET /admin/dashboard/"""

    def test_returns_the_dashboard_data(self, client, controller):
        """Test the controller's dict reaches the response body."""

        response = client.get("/admin/dashboard/")

        assert response.status_code == 200
        assert response.json()["data"]["data"] == DASHBOARD
        controller.get_dashboard.assert_awaited_once()

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot see the admin dashboard."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/admin/dashboard/")

        assert response.status_code == 403
        controller.get_dashboard.assert_not_called()

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot see the admin dashboard."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/admin/dashboard/")

        assert response.status_code == 403

    def test_without_a_token_returns_401(self, client, controller, auth):
        """Test an anonymous request is rejected."""

        auth.anonymous()

        response = client.get("/admin/dashboard/")

        assert response.status_code == 401
