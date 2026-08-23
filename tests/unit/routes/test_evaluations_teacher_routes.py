"""
Tests for the teacher-scoped evaluation routes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluations import get_evaluations_controller
from api.routes.evaluations import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER

TEACHER_DETAIL = {
    "evaluation_id": 12,
    "teacher_id": 5,
    "period_name": "2025-1",
    "courses": [{"course_code": "1155101", "average": 4.3}],
    "previous_period": None,
}

TEACHER_COMMENTS = {
    "teacher_id": 5,
    "courses": [
        {
            "course_code": "1155101",
            "course_name": "Cálculo I",
            "comments": [{"id": 1, "original_text": "Buen docente"}],
        }
    ],
}


@pytest.fixture
def controller():
    """Mock EvaluationsController."""

    mock = MagicMock()
    mock.get_teacher_detail = AsyncMock()
    mock.get_teacher_comments = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the evaluations router."""

    return make_client(router, {get_evaluations_controller: controller})


class TestGetTeacherEvaluationDetail:
    """Test suite for GET /evaluations/teachers/{teacher_id}/detail."""

    async def test_returns_the_detail(self, client, controller):
        """The controller result is returned inside the envelope."""

        controller.get_teacher_detail.return_value = TEACHER_DETAIL

        response = client.get(
            "/evaluations/teachers/5/detail", params={"period_name": "2025-1"}
        )

        assert response.status_code == 200
        assert response.json()["data"] == TEACHER_DETAIL

    async def test_does_not_compare_with_the_previous_period_by_default(
        self, client, controller
    ):
        """compare_previous defaults to False."""

        controller.get_teacher_detail.return_value = TEACHER_DETAIL

        client.get("/evaluations/teachers/5/detail", params={"period_name": "2025-1"})

        args = controller.get_teacher_detail.call_args
        assert args.args == ("2025-1", 5)
        assert args.kwargs == {"compare_previous": False}

    async def test_forwards_compare_previous(self, client, controller):
        """The flag reaches the controller as a keyword argument."""

        controller.get_teacher_detail.return_value = TEACHER_DETAIL

        client.get(
            "/evaluations/teachers/5/detail",
            params={"period_name": "2025-1", "compare_previous": "true"},
        )

        assert controller.get_teacher_detail.call_args.kwargs == {
            "compare_previous": True
        }

    async def test_requires_the_period_name(self, client, controller):
        """period_name has no default."""

        response = client.get("/evaluations/teachers/5/detail")

        assert response.status_code == 422
        controller.get_teacher_detail.assert_not_called()

    async def test_returns_404_when_there_is_no_detail(self, client, controller):
        """A None from the controller becomes a 404."""

        controller.get_teacher_detail.return_value = None

        response = client.get(
            "/evaluations/teachers/999/detail", params={"period_name": "2025-1"}
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["error"]["message"]

    async def test_director_may_read_it(self, client, controller, auth):
        """DIRECTOR is among the allowed roles."""

        auth.as_user(DIRECTOR_USER)
        controller.get_teacher_detail.return_value = TEACHER_DETAIL

        response = client.get(
            "/evaluations/teachers/5/detail", params={"period_name": "2025-1"}
        )

        assert response.status_code == 200

    async def test_docente_is_forbidden(self, client, controller, auth):
        """Only ADMIN and DIRECTOR may read the evaluation detail."""

        auth.as_user(DOCENTE_USER)

        response = client.get(
            "/evaluations/teachers/5/detail", params={"period_name": "2025-1"}
        )

        assert response.status_code == 403
        controller.get_teacher_detail.assert_not_called()

    async def test_requires_authentication(self, client, controller, auth):
        """Without a token the request is rejected."""

        auth.anonymous()

        response = client.get(
            "/evaluations/teachers/5/detail", params={"period_name": "2025-1"}
        )

        assert response.status_code == 401
        controller.get_teacher_detail.assert_not_called()


class TestGetTeacherComments:
    """Test suite for GET /evaluations/{id}/teachers/{id}/comments."""

    async def test_returns_the_comments_grouped_by_course(self, client, controller):
        """The controller result is returned inside the envelope."""

        controller.get_teacher_comments.return_value = TEACHER_COMMENTS

        response = client.get("/evaluations/12/teachers/5/comments")

        assert response.status_code == 200
        assert response.json()["data"] == TEACHER_COMMENTS

    async def test_forwards_both_path_ids(self, client, controller):
        """The evaluation and the teacher come from the path, in that order."""

        controller.get_teacher_comments.return_value = TEACHER_COMMENTS

        client.get("/evaluations/12/teachers/5/comments")

        assert controller.get_teacher_comments.call_args.args == (12, 5)

    async def test_returns_404_when_there_are_no_comments(self, client, controller):
        """A falsy result from the controller becomes a 404."""

        controller.get_teacher_comments.return_value = None

        response = client.get("/evaluations/12/teachers/999/comments")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["error"]["message"]

    async def test_rejects_a_non_numeric_evaluation_id(self, client, controller):
        """The path parameters are typed as integers."""

        response = client.get("/evaluations/abc/teachers/5/comments")

        assert response.status_code == 422
        controller.get_teacher_comments.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """Only ADMIN and DIRECTOR may read the comments of an evaluation."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluations/12/teachers/5/comments")

        assert response.status_code == 403
        controller.get_teacher_comments.assert_not_called()
