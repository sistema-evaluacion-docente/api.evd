"""Tests for the faculties routes.

What the route layer owns here: the widened read-role guard
(ADMIN/VICERRECTOR_ACADEMICO/DECANO), the ADMIN-only write and
dean-assignment guards, mapping a ``None``/falsy result from the controller
to a 404, and translating a dean-assignment ``ValueError`` into a 400.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.faculties import get_faculties_controller
from api.routes.faculties import router
from tests.unit.routes.conftest import (
    DECANO_USER,
    DIRECTOR_USER,
    DOCENTE_USER,
    VICERRECTOR_USER,
    paginated,
)

FACULTY = {
    "id": 1,
    "code": "ENG",
    "name": "Engineering",
    "active": True,
    "department_count": 0,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

DEAN = {
    "id": 1,
    "user_id": 10,
    "faculty_id": 1,
    "active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock FacultiesController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    mock.assign_dean = AsyncMock()
    mock.unassign_dean = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the faculties router."""

    return make_client(router, {get_faculties_controller: controller})


class TestListFaculties:
    """GET /faculties/"""

    def test_returns_items_and_pagination(self, client, controller):
        controller.get_all.return_value = paginated([FACULTY])

        response = client.get("/faculties/")

        assert response.status_code == 200
        assert response.json()["data"] == [FACULTY]

    def test_for_a_decano_returns_200(self, client, controller, auth):
        auth.as_user(DECANO_USER)
        controller.get_all.return_value = paginated([FACULTY])

        response = client.get("/faculties/")

        assert response.status_code == 200

    def test_for_a_vicerrector_returns_200(self, client, controller, auth):
        auth.as_user(VICERRECTOR_USER)
        controller.get_all.return_value = paginated([FACULTY])

        response = client.get("/faculties/")

        assert response.status_code == 200

    def test_for_a_director_returns_403(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)

        response = client.get("/faculties/")

        assert response.status_code == 403


class TestGetFaculty:
    """GET /faculties/{faculty_id}"""

    def test_when_faculty_exists_returns_200(self, client, controller):
        controller.get_by_id.return_value = FACULTY

        response = client.get("/faculties/1")

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        controller.get_by_id.return_value = None

        response = client.get("/faculties/999")

        assert response.status_code == 404

    def test_for_a_decano_returns_200(self, client, controller, auth):
        auth.as_user(DECANO_USER)
        controller.get_by_id.return_value = FACULTY

        response = client.get("/faculties/1")

        assert response.status_code == 200


class TestCreateFaculty:
    """POST /faculties/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        controller.create.return_value = FACULTY

        response = client.post(
            "/faculties/", json={"code": "ENG", "name": "Engineering"}
        )

        assert response.status_code == 201

    def test_for_a_decano_returns_403(self, client, controller, auth):
        auth.as_user(DECANO_USER)

        response = client.post(
            "/faculties/", json={"code": "ENG", "name": "Engineering"}
        )

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestUpdateFaculty:
    """PUT /faculties/{faculty_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        controller.update.return_value = {**FACULTY, "name": "Engineering II"}

        response = client.put("/faculties/1", json={"name": "Engineering II"})

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        controller.update.return_value = None

        response = client.put("/faculties/999", json={"name": "Engineering II"})

        assert response.status_code == 404


class TestDeleteFaculty:
    """DELETE /faculties/{faculty_id}"""

    def test_when_faculty_exists_returns_200(self, client, controller):
        controller.delete.return_value = FACULTY

        response = client.delete("/faculties/1")

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        controller.delete.return_value = None

        response = client.delete("/faculties/999")

        assert response.status_code == 404


class TestAssignDean:
    """POST /faculties/{faculty_id}/dean"""

    def test_with_valid_payload_returns_200(self, client, controller):
        controller.assign_dean.return_value = DEAN

        response = client.post("/faculties/1/dean", json={"user_id": 10})

        assert response.status_code == 200
        assert response.json()["data"]["user_id"] == 10

    def test_when_assignment_fails_returns_400(self, client, controller):
        controller.assign_dean.side_effect = ValueError(
            "Este usuario ya es decano de otra facultad"
        )

        response = client.post("/faculties/1/dean", json={"user_id": 10})

        assert response.status_code == 400

    def test_for_a_decano_returns_403(self, client, controller, auth):
        auth.as_user(DECANO_USER)

        response = client.post("/faculties/1/dean", json={"user_id": 10})

        assert response.status_code == 403
        controller.assign_dean.assert_not_called()

    def test_for_a_docente_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.post("/faculties/1/dean", json={"user_id": 10})

        assert response.status_code == 403


class TestUnassignDean:
    """DELETE /faculties/{faculty_id}/dean"""

    def test_when_dean_exists_returns_204(self, client, controller):
        controller.unassign_dean.return_value = DEAN

        response = client.delete("/faculties/1/dean")

        assert response.status_code == 204

    def test_when_dean_missing_returns_404(self, client, controller):
        controller.unassign_dean.return_value = None

        response = client.delete("/faculties/1/dean")

        assert response.status_code == 404

    def test_for_a_decano_returns_403(self, client, controller, auth):
        auth.as_user(DECANO_USER)

        response = client.delete("/faculties/1/dean")

        assert response.status_code == 403
        controller.unassign_dean.assert_not_called()
