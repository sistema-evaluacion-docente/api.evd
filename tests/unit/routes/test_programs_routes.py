"""
Tests for the programs routes.

What the route layer owns here: the ADMIN-only guard, the paginated envelope of
the list endpoint, mapping a ``None`` from the controller to a 404, and the
translation of a domain exception into its HTTP status.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.programs import get_programs_controller
from api.exceptions import ResourceAlreadyExistsError
from api.routes.programs import router
from tests.unit.routes.conftest import (
    DIRECTOR_USER,
    DOCENTE_USER,
    paginated,
)

PROGRAM = {
    "id": 1,
    "name": "Ingeniería de Sistemas",
    "code": "IS",
    "active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock ProgramsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the programs router."""

    return make_client(router, {get_programs_controller: controller})


class TestListPrograms:
    """GET /programs/"""

    def test_returns_items_and_pagination_in_the_envelope(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([PROGRAM])

        response = client.get("/programs/")

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [PROGRAM]
        assert body["pagination"]["total"] == 1
        assert body["pagination"]["page"] == 1

    def test_forwards_filters_to_the_controller(self, client, controller):
        """Test the query parameters reach the controller as filters."""

        controller.get_all.return_value = paginated([])

        response = client.get("/programs/?search=Sistemas&active=false&page=2&limit=5")

        assert response.status_code == 200
        filters, pagination = controller.get_all.call_args.args
        assert filters.search == "Sistemas"
        assert filters.active is False
        assert pagination.page == 2
        assert pagination.limit == 5

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list programs."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/programs/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot list programs."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/programs/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()

    def test_without_a_token_returns_401(self, client, controller, auth):
        """Test an anonymous request is rejected."""

        auth.anonymous()

        response = client.get("/programs/")

        assert response.status_code == 401
        controller.get_all.assert_not_called()


class TestGetProgram:
    """GET /programs/{program_id}"""

    def test_when_program_exists_returns_200(self, client, controller):
        """Test an existing program is returned in the envelope."""

        controller.get_by_id.return_value = PROGRAM

        response = client.get("/programs/1")

        assert response.status_code == 200
        assert response.json()["data"]["code"] == "IS"
        controller.get_by_id.assert_called_once_with(1)

    def test_when_program_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/programs/999")

        assert response.status_code == 404


class TestCreateProgram:
    """POST /programs/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the program."""

        controller.create.return_value = PROGRAM

        response = client.post(
            "/programs/", json={"name": "Ingeniería de Sistemas", "code": "IS"}
        )

        assert response.status_code == 201
        assert response.json()["data"]["id"] == 1

    def test_passes_the_current_user_to_the_controller(self, client, controller):
        """Test the authenticated user reaches the controller for the audit."""

        controller.create.return_value = PROGRAM

        client.post("/programs/", json={"name": "Ingeniería de Sistemas", "code": "IS"})

        _data, current_user = controller.create.call_args.args
        assert current_user["roles"] == ["ADMIN"]

    def test_with_missing_code_returns_422(self, client, controller):
        """Test an incomplete payload fails schema validation."""

        response = client.post("/programs/", json={"name": "Ingeniería de Sistemas"})

        assert response.status_code == 422
        controller.create.assert_not_called()

    def test_with_duplicate_code_returns_409(self, client, controller):
        """Test the domain exception is translated to its HTTP status."""

        controller.create.side_effect = ResourceAlreadyExistsError(
            "Program", "code", "IS"
        )

        response = client.post(
            "/programs/", json={"name": "Ingeniería de Sistemas", "code": "IS"}
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "RESOURCE_ALREADY_EXISTS"

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot create programs."""

        auth.as_user(DIRECTOR_USER)

        response = client.post(
            "/programs/", json={"name": "Ingeniería de Sistemas", "code": "IS"}
        )

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestUpdateProgram:
    """PUT /programs/{program_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the program."""

        controller.update.return_value = {**PROGRAM, "name": "Ingeniería Industrial"}

        response = client.put("/programs/1", json={"name": "Ingeniería Industrial"})

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Ingeniería Industrial"

    def test_when_program_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/programs/999", json={"name": "Ingeniería Industrial"})

        assert response.status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot update programs."""

        auth.as_user(DIRECTOR_USER)

        response = client.put("/programs/1", json={"name": "Ingeniería Industrial"})

        assert response.status_code == 403
        controller.update.assert_not_called()


class TestDeleteProgram:
    """DELETE /programs/{program_id}"""

    def test_when_program_exists_returns_200(self, client, controller):
        """Test deleting an existing program returns it."""

        controller.delete.return_value = PROGRAM

        response = client.delete("/programs/1")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == 1

    def test_when_program_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/programs/999")

        assert response.status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot delete programs."""

        auth.as_user(DIRECTOR_USER)

        response = client.delete("/programs/1")

        assert response.status_code == 403
        controller.delete.assert_not_called()
