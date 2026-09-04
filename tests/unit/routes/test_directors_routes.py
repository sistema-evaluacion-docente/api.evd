"""Tests for the directors routes.

What the route layer owns here: the ADMIN-only guard, unwrapping
``get_all``'s paginated dict into a bare list, and mapping a ``None`` from
the controller to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.directors import get_directors_controller
from api.routes.directors import router
from tests.unit.routes.conftest import DIRECTOR_USER, paginated

DIRECTOR = {
    "id": 2,
    "institutional_code": "12345",
    "user_id": 2,
    "department_id": 7,
    "active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock DirectorsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the directors router."""

    return make_client(router, {get_directors_controller: controller})


class TestListDirectors:
    """GET /directors/"""

    def test_returns_the_items(self, client, controller):
        """Test the paginated dict's items reach the response body."""

        controller.get_all.return_value = paginated([DIRECTOR])

        response = client.get("/directors/")

        assert response.status_code == 200
        assert response.json()["data"] == [DIRECTOR]

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list directors."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/directors/")

        assert response.status_code == 403


class TestGetDirector:
    """GET /directors/{director_id}"""

    def test_when_director_exists_returns_200(self, client, controller):
        """Test an existing director is returned."""

        controller.get_by_id.return_value = DIRECTOR

        response = client.get("/directors/2")

        assert response.status_code == 200

    def test_when_director_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/directors/999")

        assert response.status_code == 404


class TestCreateDirector:
    """POST /directors/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the director."""

        controller.create.return_value = DIRECTOR

        response = client.post(
            "/directors/",
            json={
                "email": "director@ufps.edu.co",
                "institutional_code": "12345",
                "department_id": 7,
            },
        )

        assert response.status_code == 201


class TestUpdateDirector:
    """PUT /directors/{director_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the director."""

        controller.update.return_value = {**DIRECTOR, "active": False}

        response = client.put("/directors/2", json={"active": False})

        assert response.status_code == 200

    def test_when_director_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/directors/999", json={"active": False})

        assert response.status_code == 404


class TestDeleteDirector:
    """DELETE /directors/{director_id}"""

    def test_when_director_exists_returns_200(self, client, controller):
        """Test deleting an existing director returns it."""

        controller.delete.return_value = DIRECTOR

        response = client.delete("/directors/2")

        assert response.status_code == 200

    def test_when_director_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/directors/999")

        assert response.status_code == 404
