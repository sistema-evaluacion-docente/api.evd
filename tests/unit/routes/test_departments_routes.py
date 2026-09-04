"""Tests for the departments routes.

What the route layer owns here: the ADMIN-only guard, mapping a ``None``
from the controller to a 404, and translating a director-assignment
``ValueError`` into a 400.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.departments import get_departments_controller
from api.controllers.directors import get_directors_controller
from api.routes.departments import router
from tests.unit.routes.conftest import DIRECTOR_USER, paginated

DEPARTMENT = {
    "id": 7,
    "code": "SIS",
    "name": "Sistemas",
    "faculty_id": 1,
    "active": True,
    "teacher_count": 0,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

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
    """Mock DepartmentsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def directors_controller():
    """Mock DirectorsController."""

    mock = MagicMock()
    mock.assign_director = AsyncMock()
    mock.unassign_director = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller, directors_controller):
    """Test client for the departments router."""

    return make_client(
        router,
        {
            get_departments_controller: controller,
            get_directors_controller: directors_controller,
        },
    )


class TestListDepartments:
    """GET /departments/"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([DEPARTMENT])

        response = client.get("/departments/")

        assert response.status_code == 200
        assert response.json()["data"] == [DEPARTMENT]

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list departments."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/departments/")

        assert response.status_code == 403


class TestGetDepartment:
    """GET /departments/{department_id}"""

    def test_when_department_exists_returns_200(self, client, controller):
        """Test an existing department is returned."""

        controller.get_by_id.return_value = DEPARTMENT

        response = client.get("/departments/7")

        assert response.status_code == 200

    def test_when_department_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/departments/999")

        assert response.status_code == 404


class TestCreateDepartment:
    """POST /departments/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the department."""

        controller.create.return_value = DEPARTMENT

        response = client.post(
            "/departments/", json={"code": "SIS", "name": "Sistemas"}
        )

        assert response.status_code == 201


class TestUpdateDepartment:
    """PUT /departments/{department_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the department."""

        controller.update.return_value = {**DEPARTMENT, "name": "Sistemas II"}

        response = client.put("/departments/7", json={"name": "Sistemas II"})

        assert response.status_code == 200

    def test_when_department_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/departments/999", json={"name": "Sistemas II"})

        assert response.status_code == 404


class TestDeleteDepartment:
    """DELETE /departments/{department_id}"""

    def test_when_department_exists_returns_200(self, client, controller):
        """Test deleting an existing department returns it."""

        controller.delete.return_value = DEPARTMENT

        response = client.delete("/departments/7")

        assert response.status_code == 200

    def test_when_department_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/departments/999")

        assert response.status_code == 404


class TestAssignDirector:
    """POST /departments/{department_id}/director"""

    def test_with_valid_payload_returns_200(self, client, directors_controller):
        """Test a valid payload assigns the director."""

        directors_controller.assign_director.return_value = DIRECTOR

        response = client.post(
            "/departments/7/director", json={"user_id": 2}
        )

        assert response.status_code == 200
        assert response.json()["data"]["id"] == 2

    def test_when_assignment_fails_returns_400(self, client, directors_controller):
        """Test a ValueError from the controller becomes a 400."""

        directors_controller.assign_director.side_effect = ValueError(
            "El usuario ya es director de otro departamento"
        )

        response = client.post(
            "/departments/7/director", json={"user_id": 2}
        )

        assert response.status_code == 400

    def test_for_a_director_returns_403(self, client, directors_controller, auth):
        """Test a director cannot assign directors."""

        auth.as_user(DIRECTOR_USER)

        response = client.post(
            "/departments/7/director", json={"user_id": 2}
        )

        assert response.status_code == 403
        directors_controller.assign_director.assert_not_called()


class TestUnassignDirector:
    """DELETE /departments/{department_id}/director"""

    def test_when_director_exists_returns_204(self, client, directors_controller):
        """Test unassigning an existing director returns 204."""

        directors_controller.unassign_director.return_value = True

        response = client.delete("/departments/7/director")

        assert response.status_code == 204

    def test_when_director_missing_returns_404(self, client, directors_controller):
        """Test a falsy result from the controller becomes a 404."""

        directors_controller.unassign_director.return_value = False

        response = client.delete("/departments/7/director")

        assert response.status_code == 404
