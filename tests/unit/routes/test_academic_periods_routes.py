"""Tests for the academic periods routes.

What the route layer owns here: ADMIN-only for the mutating endpoints, a
wider read role set for listing, and mapping a ``None`` from the controller
to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.academic_periods import get_academic_periods_controller
from api.routes.academic_periods import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER, paginated

PERIOD = {
    "id": 1,
    "code": "2026-1",
    "name": "2026-1",
    "active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock AcademicPeriodsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.activate = AsyncMock()
    mock.close = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the academic periods router."""

    return make_client(router, {get_academic_periods_controller: controller})


class TestListAcademicPeriods:
    """GET /academic-periods/"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([PERIOD])

        response = client.get("/academic-periods/")

        assert response.status_code == 200
        assert response.json()["data"] == [PERIOD]

    def test_is_readable_by_a_teacher(self, client, controller, auth):
        """Test a teacher can list academic periods."""

        auth.as_user(DOCENTE_USER)
        controller.get_all.return_value = paginated([])

        response = client.get("/academic-periods/")

        assert response.status_code == 200


class TestGetAcademicPeriod:
    """GET /academic-periods/{period_id}"""

    def test_when_period_exists_returns_200(self, client, controller):
        """Test an existing period is returned."""

        controller.get_by_id.return_value = PERIOD

        response = client.get("/academic-periods/1")

        assert response.status_code == 200

    def test_when_period_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/academic-periods/999")

        assert response.status_code == 404


class TestCreateAcademicPeriod:
    """POST /academic-periods/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the period."""

        controller.create.return_value = PERIOD

        response = client.post("/academic-periods/", json={"name": "2026-1"})

        assert response.status_code == 201

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test only ADMIN can create academic periods."""

        auth.as_user(DIRECTOR_USER)

        response = client.post("/academic-periods/", json={"name": "2026-1"})

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestUpdateAcademicPeriod:
    """PUT /academic-periods/{period_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the period."""

        controller.update.return_value = {**PERIOD, "name": "2026-2"}

        response = client.put("/academic-periods/1", json={"name": "2026-2"})

        assert response.status_code == 200

    def test_when_period_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/academic-periods/999", json={"name": "2026-2"})

        assert response.status_code == 404


class TestActivateAcademicPeriod:
    """PATCH /academic-periods/{period_id}/activate"""

    def test_when_period_exists_returns_200(self, client, controller):
        """Test activating an existing period returns it."""

        controller.activate.return_value = PERIOD

        response = client.patch("/academic-periods/1/activate")

        assert response.status_code == 200

    def test_when_period_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.activate.return_value = None

        response = client.patch("/academic-periods/999/activate")

        assert response.status_code == 404


class TestCloseAcademicPeriod:
    """PATCH /academic-periods/{period_id}/close"""

    def test_when_period_exists_returns_200(self, client, controller):
        """Test closing an existing period returns it."""

        controller.close.return_value = {**PERIOD, "active": False}

        response = client.patch("/academic-periods/1/close")

        assert response.status_code == 200

    def test_when_period_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.close.return_value = None

        response = client.patch("/academic-periods/999/close")

        assert response.status_code == 404


class TestDeleteAcademicPeriod:
    """DELETE /academic-periods/{period_id}"""

    def test_when_period_exists_returns_200(self, client, controller):
        """Test deleting an existing period returns it."""

        controller.delete.return_value = PERIOD

        response = client.delete("/academic-periods/1")

        assert response.status_code == 200

    def test_when_period_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/academic-periods/999")

        assert response.status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test only ADMIN can delete academic periods."""

        auth.as_user(DIRECTOR_USER)

        response = client.delete("/academic-periods/1")

        assert response.status_code == 403
