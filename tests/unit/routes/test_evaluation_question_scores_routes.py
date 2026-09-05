"""Tests for the evaluation question scores routes.

What the route layer owns here: the ADMIN/DIRECTOR guard and mapping a
``None`` from the controller to a logical 404 inside the manual
``ResponseSchema`` envelope.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluation_question_scores import (
    get_evaluation_question_scores_controller,
)
from api.routes.evaluation_question_scores import router
from tests.unit.routes.conftest import DOCENTE_USER

QUESTION_SCORE = {"id": 1, "evaluation_score_id": 1, "question_code": "P1", "score": 4.5}


@pytest.fixture
def controller():
    """Mock EvaluationQuestionScoresController."""

    mock = MagicMock()
    mock.get_by_id = AsyncMock()
    mock.get_by_evaluation_score = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the evaluation question scores router."""

    return make_client(
        router, {get_evaluation_question_scores_controller: controller}
    )


class TestGetEvaluationQuestionScoreById:
    """GET /evaluation-question-scores/{question_score_id}"""

    def test_when_score_exists_returns_it(self, client, controller):
        """Test an existing question score reaches the response body."""

        controller.get_by_id.return_value = QUESTION_SCORE

        response = client.get("/evaluation-question-scores/1")

        assert response.status_code == 200
        assert response.json()["data"]["data"] == QUESTION_SCORE
        controller.get_by_id.assert_called_once_with(1)

    def test_when_score_missing_returns_logical_404(self, client, controller):
        """Test a None from the controller becomes a logical 404."""

        controller.get_by_id.return_value = None

        response = client.get("/evaluation-question-scores/999")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == 404

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot read question scores."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluation-question-scores/1")

        assert response.status_code == 403
        controller.get_by_id.assert_not_called()


class TestGetQuestionScoresByEvaluationScore:
    """GET /evaluation-question-scores/by-evaluation-score/{evaluation_score_id}"""

    def test_returns_the_list(self, client, controller):
        """Test the controller's list reaches the response body."""

        controller.get_by_evaluation_score.return_value = [QUESTION_SCORE]

        response = client.get(
            "/evaluation-question-scores/by-evaluation-score/1"
        )

        assert response.status_code == 200
        assert response.json()["data"]["data"] == [QUESTION_SCORE]
        controller.get_by_evaluation_score.assert_called_once_with(1)

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot read question scores."""

        auth.as_user(DOCENTE_USER)

        response = client.get(
            "/evaluation-question-scores/by-evaluation-score/1"
        )

        assert response.status_code == 403
