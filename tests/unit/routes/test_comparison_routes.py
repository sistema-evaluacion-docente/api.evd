"""Tests for the teacher comparison route.

What the route layer owns here: any authenticated user may call it (no role
guard), and a ``None`` from the controller becomes a logical 404 inside the
manual ``ResponseSchema`` envelope rather than an HTTP 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.comparison import get_comparison_controller
from api.routes.comparison import router
from tests.unit.routes.conftest import DOCENTE_USER

COMPARISON = {"teacher_id": 1, "teacher_name": "Juan Pérez"}


@pytest.fixture
def controller():
    """Mock ComparisonController."""

    mock = MagicMock()
    mock.compare_teachers_semesters = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the comparison router."""

    return make_client(router, {get_comparison_controller: controller})


class TestCompareTeachersSemesters:
    """GET /comparison/teachers"""

    def test_when_data_exists_returns_it(self, client, controller):
        """Test the controller's dict reaches the response body."""

        controller.compare_teachers_semesters.return_value = COMPARISON

        response = client.get(
            "/comparison/teachers?current_semester=2&old_semester=1&teacher_id=1"
        )

        assert response.status_code == 200
        assert response.json()["data"]["data"] == COMPARISON
        controller.compare_teachers_semesters.assert_awaited_once_with(
            teacher_id=1, current_semester_id=2, old_semester_id=1
        )

    def test_when_result_is_none_returns_logical_404(self, client, controller):
        """Test a None result is reported as a 404 inside the envelope."""

        controller.compare_teachers_semesters.return_value = None

        response = client.get(
            "/comparison/teachers?current_semester=2&old_semester=1&teacher_id=1"
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == 404

    def test_any_authenticated_role_is_allowed(self, client, controller, auth):
        """Test the route has no role guard, just authentication."""

        auth.as_user(DOCENTE_USER)
        controller.compare_teachers_semesters.return_value = COMPARISON

        response = client.get(
            "/comparison/teachers?current_semester=2&old_semester=1&teacher_id=1"
        )

        assert response.status_code == 200

    def test_missing_query_params_returns_422(self, client, controller):
        """Test the required query parameters are enforced."""

        response = client.get("/comparison/teachers")

        assert response.status_code == 422
        controller.compare_teachers_semesters.assert_not_called()
