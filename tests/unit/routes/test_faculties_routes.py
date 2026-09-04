"""Tests for the faculties routes.

What the route layer owns here: the ADMIN-only guard and mapping a ``None``
from the controller to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.faculties import get_faculties_controller
from api.routes.faculties import router
from tests.unit.routes.conftest import DIRECTOR_USER, paginated

FACULTY = {
    "id": 1,
    "name": "Ingenierías",
    "code": "ING",
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
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the faculties router."""

    return make_client(router, {get_faculties_controller: controller})


class TestListFaculties:
    """GET /faculties/"""

    def test_returns_the_items(self, client, controller):
        """Test the controller's items reach the response body."""

        controller.get_all.return_value = paginated([FACULTY])

        response = client.get("/faculties/")

        assert response.status_code == 200
        assert response.json()["data"] == [FACULTY]

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list faculties."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/faculties/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()


class TestGetFaculty:
    """GET /faculties/{faculty_id}"""

    def test_when_faculty_exists_returns_200(self, client, controller):
        """Test an existing faculty is returned."""

        controller.get_by_id.return_value = FACULTY

        response = client.get("/faculties/1")

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/faculties/999")

        assert response.status_code == 404


class TestCreateFaculty:
    """POST /faculties/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the faculty."""

        controller.create.return_value = FACULTY

        response = client.post(
            "/faculties/", json={"name": "Ingenierías", "code": "ING"}
        )

        assert response.status_code == 201

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot create faculties."""

        auth.as_user(DIRECTOR_USER)

        response = client.post(
            "/faculties/", json={"name": "Ingenierías", "code": "ING"}
        )

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestUpdateFaculty:
    """PUT /faculties/{faculty_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the faculty."""

        controller.update.return_value = {**FACULTY, "name": "Ciencias"}

        response = client.put("/faculties/1", json={"name": "Ciencias"})

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/faculties/999", json={"name": "Ciencias"})

        assert response.status_code == 404


class TestDeleteFaculty:
    """DELETE /faculties/{faculty_id}"""

    def test_when_faculty_exists_returns_200(self, client, controller):
        """Test deleting an existing faculty returns it."""

        controller.delete.return_value = FACULTY

        response = client.delete("/faculties/1")

        assert response.status_code == 200

    def test_when_faculty_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/faculties/999")

        assert response.status_code == 404
