"""Tests for the evaluation scores routes.

What the route layer owns here: the ADMIN/DIRECTOR guard, mapping a ``None``
from the controller to a logical 404, and building the ``Pagination`` block
for the by-evaluation listing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluation_scores import get_evaluation_scores_controller
from api.routes.evaluation_scores import router
from tests.unit.routes.conftest import DOCENTE_USER

SCORE = {
    "id": 1,
    "evaluation_id": 1,
    "academic_group_id": 1,
    "respondent_count": 20,
    "overall_average": 4.2,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock EvaluationScoresController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.get_by_evaluation_paginated = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the evaluation scores router."""

    return make_client(router, {get_evaluation_scores_controller: controller})


class TestGetAllEvaluationScores:
    """GET /evaluation-scores/"""

    def test_returns_the_list(self, client, controller):
        """Test the controller's list reaches the response body."""

        controller.get_all.return_value = [SCORE]

        response = client.get("/evaluation-scores/")

        assert response.status_code == 200
        assert response.json()["data"]["data"] == [SCORE]

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot list evaluation scores."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluation-scores/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()


class TestGetEvaluationScoreById:
    """GET /evaluation-scores/{score_id}"""

    def test_when_score_exists_returns_it(self, client, controller):
        """Test an existing score reaches the response body."""

        controller.get_by_id.return_value = SCORE

        response = client.get("/evaluation-scores/1")

        assert response.status_code == 200
        assert response.json()["data"]["data"] == SCORE

    def test_when_score_missing_returns_logical_404(self, client, controller):
        """Test a None from the controller becomes a logical 404."""

        controller.get_by_id.return_value = None

        response = client.get("/evaluation-scores/999")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == 404


class TestGetScoresByEvaluation:
    """GET /evaluation-scores/by-evaluation/{evaluation_id}"""

    def test_returns_scores_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_by_evaluation_paginated.return_value = {
            "scores": [SCORE],
            "total": 1,
            "pages": 1,
        }

        response = client.get("/evaluation-scores/by-evaluation/1?page=1&limit=10")

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["data"] == [SCORE]
        assert body["pagination"]["total"] == 1
        controller.get_by_evaluation_paginated.assert_called_once_with(
            1, page=1, limit=10, search=None
        )

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot list scores by evaluation."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluation-scores/by-evaluation/1")

        assert response.status_code == 403
