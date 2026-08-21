"""
Tests for the comment routes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.comments import get_comments_controller
from api.exceptions import PermissionDeniedError, ResourceNotFoundError
from api.routes.comments import router
from tests.unit.routes.conftest import ADMIN_USER, DIRECTOR_USER, DOCENTE_USER

COMMENT = {
    "id": 31,
    "teacher_id": 5,
    "evaluation_id": 12,
    "original_text": "El docente llega tarde",
    "risk_level": {"id": 3, "name": "ALTO"},
    "pedagogical_categories": [{"id": 2, "name": "Puntualidad"}],
    "risk_level_modified_by_director": True,
    "pedagogical_category_modified_by_director": True,
}


@pytest.fixture
def controller():
    """Mock CommentsController."""

    mock = MagicMock()
    mock.update_classification = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller, auth):
    """Test client for the comments router, authenticated as a director."""

    auth.as_user(DIRECTOR_USER)
    return make_client(router, {get_comments_controller: controller})


class TestUpdateCommentClassification:
    """Test suite for PATCH /comments/{comment_id}."""

    async def test_updates_and_returns_the_comment(self, client, controller):
        """The controller result is returned inside the envelope."""

        controller.update_classification.return_value = COMMENT

        response = client.patch(
            "/comments/31",
            json={"risk_level": 3, "pedagogical_category_ids": [2]},
        )

        assert response.status_code == 200
        assert response.json()["data"] == COMMENT

    async def test_forwards_the_payload_and_the_director(self, client, controller):
        """The service needs the director to authorize and audit the change."""

        controller.update_classification.return_value = COMMENT

        client.patch(
            "/comments/31", json={"risk_level": 3, "pedagogical_category_ids": [2, 4]}
        )

        comment_id, payload, current_user = (
            controller.update_classification.call_args.args
        )
        assert comment_id == 31
        assert payload.risk_level == 3
        assert payload.pedagogical_category_ids == [2, 4]
        assert current_user["department_id"] == DIRECTOR_USER["department_id"]

    async def test_accepts_only_the_risk_level(self, client, controller):
        """Categories stay untouched when only risk_level is sent."""

        controller.update_classification.return_value = COMMENT

        response = client.patch("/comments/31", json={"risk_level": 1})

        assert response.status_code == 200
        payload = controller.update_classification.call_args.args[1]
        assert payload.risk_level == 1
        assert payload.pedagogical_category_ids is None

    async def test_an_empty_category_list_clears_the_categories(
        self, client, controller
    ):
        """An empty list is a real value, not a missing field."""

        controller.update_classification.return_value = {
            **COMMENT,
            "pedagogical_categories": [],
        }

        response = client.patch("/comments/31", json={"pedagogical_category_ids": []})

        assert response.status_code == 200
        payload = controller.update_classification.call_args.args[1]
        assert payload.pedagogical_category_ids == []
        assert payload.risk_level is None

    async def test_rejects_an_empty_payload(self, client, controller):
        """At least one of the two fields must be provided."""

        response = client.patch("/comments/31", json={})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        controller.update_classification.assert_not_called()

    async def test_returns_404_when_the_comment_does_not_exist(
        self, client, controller
    ):
        """A None from the controller becomes a 404."""

        controller.update_classification.return_value = None

        response = client.patch("/comments/999", json={"risk_level": 3})

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Comentario no encontrado"

    async def test_maps_a_foreign_department_to_403(self, client, controller):
        """PermissionDeniedError from the service becomes an error envelope."""

        controller.update_classification.side_effect = PermissionDeniedError(
            "Solo el director del departamento asociado puede modificar este comentario"
        )

        response = client.patch("/comments/31", json={"risk_level": 3})

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_maps_an_unknown_risk_level_to_404(self, client, controller):
        """ResourceNotFoundError from the service becomes an error envelope."""

        controller.update_classification.side_effect = ResourceNotFoundError(
            "Nivel de riesgo", 99
        )

        response = client.patch("/comments/31", json={"risk_level": 99})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    async def test_admin_is_forbidden(self, client, controller, auth):
        """Only the department director may reclassify a comment."""

        auth.as_user(ADMIN_USER)

        response = client.patch("/comments/31", json={"risk_level": 3})

        assert response.status_code == 403
        controller.update_classification.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """Only the department director may reclassify a comment."""

        auth.as_user(DOCENTE_USER)

        response = client.patch("/comments/31", json={"risk_level": 3})

        assert response.status_code == 403
        controller.update_classification.assert_not_called()

    async def test_requires_authentication(self, client, controller, auth):
        """Without a token the request is rejected."""

        auth.anonymous()

        response = client.patch("/comments/31", json={"risk_level": 3})

        assert response.status_code == 401
        controller.update_classification.assert_not_called()
