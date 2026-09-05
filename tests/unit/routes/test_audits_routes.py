"""Tests for the audits routes.

What the route layer owns here: the ADMIN-only guard, the paginated envelope
of the list endpoint, and mapping a ``None`` from the controller to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.audits import get_audits_controller
from api.routes.audits import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER, paginated

AUDIT = {
    "id": 1,
    "user_id": 1,
    "table_name": "users",
    "operation": "CREATE",
    "element": "1",
    "description": "Se creó el usuario",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock AuditsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the audits router."""

    return make_client(router, {get_audits_controller: controller})


class TestListAudits:
    """GET /audits/"""

    def test_returns_items_and_pagination_in_the_envelope(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([AUDIT])

        response = client.get("/audits/")

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [AUDIT]
        assert body["pagination"]["total"] == 1

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list audit logs."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/audits/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot list audit logs."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/audits/")

        assert response.status_code == 403


class TestGetAudit:
    """GET /audits/{audit_id}"""

    def test_when_audit_exists_returns_200(self, client, controller):
        """Test an existing audit log is returned in the envelope."""

        controller.get_by_id.return_value = AUDIT

        response = client.get("/audits/1")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == 1
        controller.get_by_id.assert_called_once_with(1)

    def test_when_audit_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/audits/999")

        assert response.status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot get an audit log."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/audits/1")

        assert response.status_code == 403
