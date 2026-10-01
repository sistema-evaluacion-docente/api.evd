"""Tests for the users routes.

What the route layer owns here: ADMIN/DIRECTOR for creation, ADMIN-only for
listing and role changes, and translating a ``None``/falsy controller result
into the domain's own auth/not-found exceptions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.users import get_users_controller
from api.routes.users import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER, paginated

USER = {
    "id": 3,
    "uid": "docente-uid",
    "email": "docente@ufps.edu.co",
    "department_id": None,
    "name": "Docente",
    "active": True,
    "avatar_url": None,
    "roles": ["DOCENTE"],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock UsersController."""

    mock = MagicMock()
    mock.create_user = AsyncMock()
    mock.get_all = AsyncMock()
    mock.login = AsyncMock()
    mock.get_by_uid = AsyncMock()
    mock.update = AsyncMock()
    mock.replace_roles = AsyncMock()
    mock.update_status = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.admin_update = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the users router."""

    return make_client(router, {get_users_controller: controller})


class TestCreateUser:
    """POST /users/"""

    def test_for_an_admin_returns_201(self, client, controller):
        """Test an admin can create a user of any role."""

        controller.create_user.return_value = USER

        response = client.post(
            "/users/", json={"email": "docente@ufps.edu.co", "roles": ["DOCENTE"]}
        )

        assert response.status_code == 201

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot create users."""

        auth.as_user(DOCENTE_USER)

        response = client.post(
            "/users/", json={"email": "docente@ufps.edu.co", "roles": ["DOCENTE"]}
        )

        assert response.status_code == 403
        controller.create_user.assert_not_called()


class TestListUsers:
    """GET /users/"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([USER])

        response = client.get("/users/")

        assert response.status_code == 200
        assert response.json()["data"] == [USER]

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test only ADMIN can list all users."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/users/")

        assert response.status_code == 403

    def test_passes_the_department_filter_to_the_controller(self, client, controller):
        """Test ?department_id= reaches the controller's filters."""

        controller.get_all.return_value = paginated([])

        response = client.get("/users/?department_id=7")

        assert response.status_code == 200
        filters = controller.get_all.await_args.args[0]
        assert filters.department_id == 7

    def test_with_non_numeric_department_returns_422(self, client, controller):
        assert client.get("/users/?department_id=abc").status_code == 422


class TestLoginUser:
    """GET /users/auth"""

    def test_when_user_exists_returns_it(self, client, controller):
        """Test an existing user is returned on login."""

        controller.login.return_value = USER

        response = client.get("/users/auth")

        assert response.status_code == 200

    def test_when_user_missing_raises_authentication_error(self, client, controller):
        """Test a None from the controller becomes an authentication error."""

        controller.login.return_value = None

        response = client.get("/users/auth")

        assert response.status_code == 401


class TestGetUserByUid:
    """GET /users/{uid}"""

    def test_when_user_exists_returns_it(self, client, controller):
        """Test an existing user is returned."""

        controller.get_by_uid.return_value = USER

        response = client.get("/users/docente-uid")

        assert response.status_code == 200

    def test_when_user_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_uid.return_value = None

        response = client.get("/users/unknown-uid")

        assert response.status_code == 404


class TestUpdateUser:
    """PUT /users/"""

    def test_updates_the_authenticated_users_profile(self, client, controller):
        """Test the payload reaches the controller with the current user."""

        controller.update.return_value = {**USER, "name": "Nuevo nombre"}

        response = client.put("/users/", json={"name": "Nuevo nombre"})

        assert response.status_code == 200
        controller.update.assert_awaited_once()


class TestReplaceUserRoles:
    """PUT /users/{uid}/roles"""

    def test_for_an_admin_returns_200(self, client, controller):
        """Test an admin can replace a user's roles."""

        controller.replace_roles.return_value = {**USER, "roles": ["ADMIN"]}

        response = client.put(
            "/users/docente-uid/roles", json={"roles": ["ADMIN"]}
        )

        assert response.status_code == 200

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot replace roles."""

        auth.as_user(DOCENTE_USER)

        response = client.put(
            "/users/docente-uid/roles", json={"roles": ["ADMIN"]}
        )

        assert response.status_code == 403


class TestGetUserById:
    """GET /users/by-id/{user_id}"""

    def test_for_an_admin_returns_200(self, client, controller):
        controller.get_by_id.return_value = USER

        assert client.get("/users/by-id/3").status_code == 200

    def test_when_user_missing_returns_404(self, client, controller):
        controller.get_by_id.return_value = None

        assert client.get("/users/by-id/999").status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)

        assert client.get("/users/by-id/3").status_code == 403


class TestAdminUpdateUser:
    """PUT /users/by-id/{user_id}"""

    def test_for_an_admin_passes_id_payload_and_user(self, client, controller):
        controller.admin_update.return_value = {**USER, "name": "Nuevo"}

        response = client.put(
            "/users/by-id/3",
            json={"name": "Nuevo", "email": "Nuevo@ufps.edu.co", "department_id": 7},
        )

        assert response.status_code == 200
        user_id, payload, current_user = controller.admin_update.await_args.args
        assert user_id == 3
        assert payload.email == "nuevo@ufps.edu.co"
        assert payload.department_id == 7
        assert "ADMIN" in current_user["roles"]

    def test_when_user_missing_returns_404(self, client, controller):
        controller.admin_update.return_value = None

        assert client.put("/users/by-id/999", json={"name": "X"}).status_code == 404

    def test_for_a_director_returns_403(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)

        response = client.put("/users/by-id/3", json={"name": "X"})

        assert response.status_code == 403
        controller.admin_update.assert_not_called()

    def test_with_non_numeric_code_returns_422(self, client, controller):
        response = client.put(
            "/users/by-id/3", json={"institutional_code": "12A4"}
        )

        assert response.status_code == 422
        controller.admin_update.assert_not_called()

    def test_with_blank_name_returns_422(self, client, controller):
        assert client.put("/users/by-id/3", json={"name": "  "}).status_code == 422

    def test_with_invalid_email_returns_422(self, client, controller):
        assert (
            client.put("/users/by-id/3", json={"email": "sin-arroba"}).status_code
            == 422
        )

    def test_with_null_active_returns_422(self, client, controller):
        assert client.put("/users/by-id/3", json={"active": None}).status_code == 422

    def test_with_empty_roles_returns_422(self, client, controller):
        assert client.put("/users/by-id/3", json={"roles": []}).status_code == 422


class TestUpdateUserStatus:
    """PATCH /users/{uid}/status"""

    def test_for_an_admin_returns_200(self, client, controller):
        """Test an admin can activate/deactivate a user."""

        controller.update_status.return_value = {**USER, "active": False}

        response = client.patch(
            "/users/docente-uid/status", json={"active": False}
        )

        assert response.status_code == 200

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot change a user's status."""

        auth.as_user(DOCENTE_USER)

        response = client.patch(
            "/users/docente-uid/status", json={"active": False}
        )

        assert response.status_code == 403
