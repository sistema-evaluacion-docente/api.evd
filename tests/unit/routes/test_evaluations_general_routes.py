"""Tests for the evaluation routes not covered by the upload/teacher-detail suites:
listing, single-evaluation lookups, the PDF download, and the management actions
(analyze, delete, activate/deactivate)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.controllers.evaluations import get_evaluations_controller
from api.routes.evaluations import router
from tests.unit.routes.conftest import ADMIN_USER, DIRECTOR_USER, DOCENTE_USER, paginated

EVALUATION = {"id": 1, "academic_period_id": 1, "department_id": 7, "active": True}


@pytest.fixture
def controller():
    """Mock EvaluationsController with every method these routes call."""

    mock = MagicMock()
    for name in (
        "get_all",
        "get_by_period",
        "get_by_id",
        "get_pdf_path",
        "get_teachers_by_period",
        "get_summary",
        "get_dimension_averages",
        "get_dimension_detail",
        "trigger_analysis",
        "delete",
        "update_status",
    ):
        setattr(mock, name, AsyncMock())
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the evaluations router, authenticated as an admin."""

    return make_client(router, {get_evaluations_controller: controller})


class TestGetQuestionCatalog:
    """GET /evaluations/questions"""

    def test_returns_the_catalog(self, client, controller):
        response = client.get("/evaluations/questions")

        assert response.status_code == 200
        assert len(response.json()["data"]) > 0

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluations/questions")

        assert response.status_code == 403


class TestGetAllEvaluations:
    """GET /evaluations/"""

    def test_returns_items_and_pagination(self, client, controller):
        controller.get_all.return_value = paginated([EVALUATION])

        response = client.get("/evaluations/")

        assert response.status_code == 200
        assert response.json()["data"] == [EVALUATION]
        args = controller.get_all.call_args.args
        assert args[0] == ADMIN_USER["email"]

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluations/")

        assert response.status_code == 403


class TestGetEvaluationByPeriod:
    """GET /evaluations/by-period/{period_id}"""

    def test_when_found_returns_200(self, client, controller):
        controller.get_by_period.return_value = EVALUATION

        response = client.get("/evaluations/by-period/1")

        assert response.status_code == 200

    def test_when_missing_returns_404(self, client, controller):
        controller.get_by_period.return_value = None

        response = client.get("/evaluations/by-period/999")

        assert response.status_code == 404


class TestGetEvaluationById:
    """GET /evaluations/{evaluation_id}"""

    def test_when_found_returns_200(self, client, controller):
        controller.get_by_id.return_value = EVALUATION

        response = client.get("/evaluations/1")

        assert response.status_code == 200
        controller.get_by_id.assert_awaited_once_with(1, None)

    def test_forwards_the_modality(self, client, controller):
        controller.get_by_id.return_value = EVALUATION

        client.get("/evaluations/1?modality=DISTANCIA")

        controller.get_by_id.assert_awaited_once_with(1, "DISTANCIA")

    def test_when_missing_returns_404(self, client, controller):
        controller.get_by_id.return_value = None

        response = client.get("/evaluations/999")

        assert response.status_code == 404


class TestDownloadEvaluationPdf:
    """GET /evaluations/{evaluation_id}/pdf"""

    def test_streams_the_file(self, client, controller, tmp_path):
        pdf_path = tmp_path / "eval.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")
        controller.get_pdf_path.return_value = str(pdf_path)

        response = client.get("/evaluations/1/pdf")

        assert response.status_code == 200

    def test_when_the_file_is_missing_on_disk_returns_404(self, client, controller):
        controller.get_pdf_path.return_value = "/tmp/does-not-exist.pdf"

        response = client.get("/evaluations/1/pdf")

        assert response.status_code == 404

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluations/1/pdf")

        assert response.status_code == 403


class TestGetTeachersByPeriod:
    """GET /evaluations/period/{period_id}/teachers"""

    def test_returns_the_paginated_result(self, client, controller):
        controller.get_teachers_by_period.return_value = {
            "teacher_count": 1,
            "page": 1,
            "limit": 10,
            "pages": 1,
            "teachers": [{"id": 5}],
        }

        response = client.get("/evaluations/period/1/teachers")

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [{"id": 5}]
        assert body["pagination"]["total"] == 1

    def test_when_missing_returns_404(self, client, controller):
        controller.get_teachers_by_period.return_value = None

        response = client.get("/evaluations/period/999/teachers")

        assert response.status_code == 404


class TestGetEvaluationSummary:
    """GET /evaluations/{evaluation_id}/summary"""

    def test_when_found_returns_200(self, client, controller):
        controller.get_summary.return_value = {"id": 1}

        response = client.get("/evaluations/1/summary")

        assert response.status_code == 200

    def test_when_missing_returns_404(self, client, controller):
        controller.get_summary.return_value = None

        response = client.get("/evaluations/999/summary")

        assert response.status_code == 404


class TestGetEvaluationDimensionAverages:
    """GET /evaluations/{evaluation_id}/dimension-averages"""

    def test_when_found_returns_200(self, client, controller):
        controller.get_dimension_averages.return_value = [{"dimension": "D1"}]

        response = client.get("/evaluations/1/dimension-averages")

        assert response.status_code == 200

    def test_when_missing_returns_404(self, client, controller):
        controller.get_dimension_averages.return_value = None

        response = client.get("/evaluations/999/dimension-averages")

        assert response.status_code == 404


class TestGetEvaluationDimensionDetail:
    """GET /evaluations/{evaluation_id}/dimensions/detail — DIRECTOR only."""

    def test_for_the_director_returns_200(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_dimension_detail.return_value = {"breakdown": []}

        response = client.get("/evaluations/1/dimensions/detail")

        assert response.status_code == 200

    def test_when_missing_returns_404(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_dimension_detail.return_value = None

        response = client.get("/evaluations/999/dimensions/detail")

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        response = client.get("/evaluations/1/dimensions/detail")

        assert response.status_code == 403


class TestAnalyzeEvaluation:
    """POST /evaluations/{evaluation_id}/analyze"""

    def test_schedules_the_analysis(self, client, controller):
        controller.trigger_analysis.return_value = EVALUATION

        with patch("api.routes.evaluations.analyze_evaluation_comments") as analyze:
            response = client.post("/evaluations/1/analyze")

        assert response.status_code == 202
        analyze.assert_called_once_with(1)

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.post("/evaluations/1/analyze")

        assert response.status_code == 403
        controller.trigger_analysis.assert_not_called()


class TestDeleteEvaluation:
    """DELETE /evaluations/{evaluation_id} — DIRECTOR only."""

    def test_for_the_director_returns_200(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.delete.return_value = EVALUATION

        response = client.delete("/evaluations/1")

        assert response.status_code == 200

    def test_when_missing_returns_404(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.delete.return_value = None

        response = client.delete("/evaluations/999")

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        response = client.delete("/evaluations/1")

        assert response.status_code == 403


class TestUpdateEvaluationStatus:
    """PATCH /evaluations/{evaluation_id}/status — DIRECTOR only."""

    def test_for_the_director_returns_200(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.update_status.return_value = {**EVALUATION, "active": False}

        response = client.patch("/evaluations/1/status", json={"active": False})

        assert response.status_code == 200
        controller.update_status.assert_awaited_once_with(1, False, DIRECTOR_USER)

    def test_when_missing_returns_404(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.update_status.return_value = None

        response = client.patch("/evaluations/999/status", json={"active": False})

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        response = client.patch("/evaluations/1/status", json={"active": False})

        assert response.status_code == 403
