"""
Tests for the settings routes.

The scoping itself lives in the service; what these cover is the wiring the
route layer owns — that a director gets past the role guard, that the
authenticated user reaches the controller so the scope can be pinned, and that
a missing setting turns into a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.settings import get_settings_controller
from api.routes.settings import router
from tests.unit.routes.conftest import (
    ADMIN_USER,
    DIRECTOR_USER,
    DOCENTE_USER,
    paginated,
)

GLOBAL_SETTING = {
    "id": 1,
    "key": "improvement_plan.score_threshold",
    "value": "3.5",
    "value_type": "NUMBER",
    "description": "Umbral institucional",
    "department_id": None,
    "department_name": None,
    "scope": "GLOBAL",
    "changed_by": None,
    "changed_by_name": None,
    "changed_by_avatar_url": None,
    "effective_from": "2026-01-01T00:00:00Z",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

DEPARTMENT_SETTING = {
    **GLOBAL_SETTING,
    "id": 2,
    "value": "3.8",
    "department_id": DIRECTOR_USER["department_id"],
    "department_name": "Ingeniería de Sistemas",
    "scope": "DEPARTMENT",
}


@pytest.fixture
def controller():
    """Mock SettingsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.get_by_key = AsyncMock()
    mock.get_history = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the settings router."""

    return make_client(router, {get_settings_controller: controller})


class TestSettingsRoleGuards:
    """Who may reach the settings endpoints."""

    async def test_a_director_can_list_settings(self, client, controller, auth):
        """A director now manages settings, not only an ADMIN."""

        auth.as_user(DIRECTOR_USER)
        controller.get_all.return_value = paginated([DEPARTMENT_SETTING])

        response = client.get("/settings/")

        assert response.status_code == 200

    async def test_a_director_can_create_a_setting(self, client, controller, auth):
        """A director creates the settings of its own department."""

        auth.as_user(DIRECTOR_USER)
        controller.create.return_value = DEPARTMENT_SETTING

        response = client.post(
            "/settings/",
            json={"key": "improvement_plan.score_threshold", "value": "3.8"},
        )

        assert response.status_code == 201
        assert response.json()["data"]["scope"] == "DEPARTMENT"

    async def test_a_teacher_is_rejected(self, client, controller, auth):
        """A DOCENTE has no business in the settings module."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/settings/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()

    async def test_an_anonymous_request_is_rejected(self, client, controller, auth):
        """No token, no settings."""

        auth.anonymous()

        response = client.get("/settings/")

        assert response.status_code == 401
        controller.get_all.assert_not_called()


class TestSettingsScopeWiring:
    """The authenticated user has to reach the controller."""

    async def test_list_forwards_the_current_user(self, client, controller, auth):
        """The service pins the scope from the user the route hands it."""

        auth.as_user(DIRECTOR_USER)
        controller.get_all.return_value = paginated([DEPARTMENT_SETTING])

        client.get("/settings/")

        _filters, _pagination, current_user = controller.get_all.call_args.args
        assert current_user["department_id"] == DIRECTOR_USER["department_id"]

    async def test_list_forwards_the_requested_department(
        self, client, controller, auth
    ):
        """The service is the one that accepts or refuses the scope asked for."""

        auth.as_user(ADMIN_USER)
        controller.get_all.return_value = paginated([GLOBAL_SETTING])

        client.get("/settings/?department_id=7&include_global=false")

        filters = controller.get_all.call_args.args[0]
        assert filters.department_id == 7
        assert filters.include_global is False

    async def test_by_key_forwards_the_user_and_department(
        self, client, controller, auth
    ):
        """The by-key lookup hands the service both the user and the scope."""

        auth.as_user(ADMIN_USER)
        controller.get_by_key.return_value = GLOBAL_SETTING

        response = client.get(
            "/settings/by-key/improvement_plan.score_threshold?department_id=7"
        )

        assert response.status_code == 200
        key, current_user, department_id = controller.get_by_key.call_args.args
        assert key == "improvement_plan.score_threshold"
        assert current_user["id"] == ADMIN_USER["id"]
        assert department_id == 7

    async def test_create_forwards_the_current_user(self, client, controller, auth):
        """The service needs the user to force the department and audit it."""

        auth.as_user(DIRECTOR_USER)
        controller.create.return_value = DEPARTMENT_SETTING

        client.post("/settings/", json={"key": "a.key", "value": "1"})

        payload, current_user = controller.create.call_args.args
        assert payload.key == "a.key"
        assert current_user["id"] == DIRECTOR_USER["id"]

    async def test_history_is_read_in_the_scope_of_its_setting(
        self, client, controller, auth
    ):
        """The history of a department's setting excludes the global entries."""

        auth.as_user(DIRECTOR_USER)
        controller.get_by_id.return_value = DEPARTMENT_SETTING
        controller.get_history.return_value = paginated([])

        response = client.get("/settings/2/history")

        assert response.status_code == 200
        kwargs = controller.get_history.call_args.kwargs
        assert kwargs["key"] == DEPARTMENT_SETTING["key"]
        assert kwargs["department_id"] == DIRECTOR_USER["department_id"]

    async def test_history_of_a_global_setting_stays_global(
        self, client, controller, auth
    ):
        """An institutional setting reads its own history, not a department's."""

        auth.as_user(ADMIN_USER)
        controller.get_by_id.return_value = GLOBAL_SETTING
        controller.get_history.return_value = paginated([])

        client.get("/settings/1/history")

        assert controller.get_history.call_args.kwargs["department_id"] is None


class TestSettingsNotFound:
    """A missing setting becomes a 404 at the route."""

    async def test_get_by_id_missing_returns_404(self, client, controller, auth):
        """The controller returning None is a 404."""

        auth.as_user(ADMIN_USER)
        controller.get_by_id.return_value = None

        response = client.get("/settings/999")

        assert response.status_code == 404

    async def test_get_by_key_missing_returns_404(self, client, controller, auth):
        """A key with no value in any scope is a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.get_by_key.return_value = None

        response = client.get("/settings/by-key/nope")

        assert response.status_code == 404

    async def test_history_of_a_missing_setting_returns_404(
        self, client, controller, auth
    ):
        """No setting, no history."""

        auth.as_user(ADMIN_USER)
        controller.get_by_id.return_value = None

        response = client.get("/settings/999/history")

        assert response.status_code == 404
        controller.get_history.assert_not_called()

    async def test_update_missing_returns_404(self, client, controller, auth):
        """Updating a setting that is not there is a 404."""

        auth.as_user(ADMIN_USER)
        controller.update.return_value = None

        response = client.put("/settings/999", json={"value": "4.0"})

        assert response.status_code == 404

    async def test_delete_missing_returns_404(self, client, controller, auth):
        """Deleting a setting that is not there is a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.delete.return_value = None

        response = client.delete("/settings/999")

        assert response.status_code == 404
