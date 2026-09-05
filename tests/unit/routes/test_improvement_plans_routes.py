"""Tests for the improvement plans routes.

What the route layer owns here: the MANAGER_ROLES/ANY_ROLE/DOCENTE-only
guards, the DIRECTOR-only (not ADMIN) delete guard, the PDF upload
validation shared by the two upload endpoints (``_read_pdf``), and building
the ``FileResponse``/``Response`` for downloads.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.controllers.improvement_plans import get_improvement_plans_controller
from api.routes.improvement_plans import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER, paginated

PLAN = {"id": 1, "teacher_id": 3, "status": "ACTIVO"}


@pytest.fixture
def controller():
    """Mock ImprovementPlansController with every method the routes call."""

    mock = MagicMock()
    for name in (
        "get_all",
        "get_at_risk",
        "get_candidates",
        "get_evaluated_periods",
        "get_indicators",
        "get_my_plans",
        "get_teacher_courses",
        "get_history",
        "create",
        "get_by_id",
        "update",
        "delete",
        "upsert_case_report",
        "update_checkpoint",
        "close_acta",
        "reopen_acta",
        "close",
        "generate_document",
        "upload_signed_document",
        "delete_signed_document",
        "list_evidence_requests",
        "create_evidence_request",
        "get_evidence_request",
        "update_evidence_request",
        "add_evidence_comment",
        "add_evidence",
        "review_evidence",
        "delete_evidence",
        "get_evidence_file",
        "render_document_word",
        "get_document_file",
    ):
        setattr(mock, name, AsyncMock())
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the improvement plans router, authenticated as director."""

    return make_client(router, {get_improvement_plans_controller: controller})


@pytest.fixture(autouse=True)
def as_director(auth):
    """Most endpoints are exercised as the director; DOCENTE-only ones override."""

    auth.as_user(DIRECTOR_USER)


class TestGetAllPlans:
    def test_returns_items_and_pagination(self, client, controller):
        controller.get_all.return_value = paginated([PLAN])

        response = client.get("/improvement-plans/")

        assert response.status_code == 200
        assert response.json()["data"] == [PLAN]


class TestGetAtRiskTeachers:
    def test_returns_the_result(self, client, controller):
        controller.get_at_risk.return_value = [{"teacher_id": 3}]

        response = client.get("/improvement-plans/at-risk?period_id=1")

        assert response.status_code == 200

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/improvement-plans/at-risk?period_id=1")

        assert response.status_code == 403


class TestGetPlanCandidates:
    def test_returns_the_result(self, client, controller):
        controller.get_candidates.return_value = [{"teacher_id": 3}]

        response = client.get("/improvement-plans/candidates?period_id=1")

        assert response.status_code == 200


class TestGetEvaluatedPeriods:
    def test_returns_the_result(self, client, controller):
        controller.get_evaluated_periods.return_value = [{"id": 1}]

        response = client.get("/improvement-plans/periods")

        assert response.status_code == 200


class TestGetPlanIndicators:
    def test_open_to_a_teacher(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)
        controller.get_indicators.return_value = {"aspects": []}

        response = client.get("/improvement-plans/indicators")

        assert response.status_code == 200


class TestGetMyPlans:
    def test_for_a_teacher_returns_200(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)
        controller.get_my_plans.return_value = [PLAN]

        response = client.get("/improvement-plans/my")

        assert response.status_code == 200

    def test_for_a_director_returns_403(self, client, controller):
        response = client.get("/improvement-plans/my")

        assert response.status_code == 403


class TestGetTeacherCourses:
    def test_returns_the_result(self, client, controller):
        controller.get_teacher_courses.return_value = [{"course_code": "BD101"}]

        response = client.get("/improvement-plans/teacher/3/courses?period_id=1")

        assert response.status_code == 200


class TestGetTeacherHistory:
    def test_returns_the_result(self, client, controller):
        controller.get_history.return_value = [{"plan_id": 1}]

        response = client.get("/improvement-plans/teacher/3/history")

        assert response.status_code == 200


class TestCreatePlan:
    def test_with_valid_payload_returns_201(self, client, controller):
        controller.create.return_value = PLAN

        response = client.post(
            "/improvement-plans/",
            json={"teacher_id": 3, "origin_period_id": 1, "title": "Plan 2026-1"},
        )

        assert response.status_code == 201

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.post(
            "/improvement-plans/",
            json={"teacher_id": 3, "origin_period_id": 1, "title": "Plan 2026-1"},
        )

        assert response.status_code == 403


class TestGetPlanById:
    def test_returns_the_plan(self, client, controller):
        controller.get_by_id.return_value = PLAN

        response = client.get("/improvement-plans/1")

        assert response.status_code == 200
        controller.get_by_id.assert_called_once_with(1, DIRECTOR_USER)


class TestUpdatePlan:
    def test_with_valid_payload_returns_200(self, client, controller):
        controller.update.return_value = {**PLAN, "title": "Nuevo título"}

        response = client.put(
            "/improvement-plans/1", json={"title": "Nuevo título"}
        )

        assert response.status_code == 200


class TestDeletePlan:
    def test_for_the_director_returns_204(self, client, controller):
        response = client.delete("/improvement-plans/1")

        assert response.status_code == 204
        controller.delete.assert_awaited_once_with(1, DIRECTOR_USER)

    def test_for_an_admin_returns_403(self, client, controller, auth):
        from tests.unit.routes.conftest import ADMIN_USER

        auth.as_user(ADMIN_USER)

        response = client.delete("/improvement-plans/1")

        assert response.status_code == 403
        controller.delete.assert_not_called()


class TestUpsertCaseReport:
    def test_returns_the_updated_plan(self, client, controller):
        controller.upsert_case_report.return_value = PLAN

        response = client.put(
            "/improvement-plans/1/case-report", json={"complaint": "Queja"}
        )

        assert response.status_code == 200


class TestUpdateCheckpoint:
    def test_returns_the_updated_plan(self, client, controller):
        controller.update_checkpoint.return_value = PLAN

        response = client.put(
            "/improvement-plans/1/checkpoints/5", json={"notes": "Avance"}
        )

        assert response.status_code == 200
        controller.update_checkpoint.assert_awaited_once()
        assert controller.update_checkpoint.call_args.args[:2] == (1, 5)


class TestCloseActa:
    def test_returns_the_updated_plan(self, client, controller):
        controller.close_acta.return_value = PLAN

        response = client.post("/improvement-plans/1/acta/close")

        assert response.status_code == 200


class TestReopenActa:
    def test_for_an_admin_returns_200(self, client, controller, auth):
        from tests.unit.routes.conftest import ADMIN_USER

        auth.as_user(ADMIN_USER)
        controller.reopen_acta.return_value = PLAN

        response = client.post("/improvement-plans/1/acta/reopen")

        assert response.status_code == 200

    def test_for_a_director_returns_403(self, client, controller):
        response = client.post("/improvement-plans/1/acta/reopen")

        assert response.status_code == 403


class TestClosePlan:
    def test_with_valid_payload_returns_200(self, client, controller):
        controller.close.return_value = {**PLAN, "status": "CERRADO"}

        response = client.post(
            "/improvement-plans/1/close", json={"result": "CUMPLIDO"}
        )

        assert response.status_code == 200


class TestGenerateDocument:
    def test_returns_the_updated_plan(self, client, controller):
        controller.generate_document.return_value = PLAN

        response = client.post("/improvement-plans/1/documents/formato-1/generate")

        assert response.status_code == 200
        controller.generate_document.assert_awaited_once_with(
            1, "formato-1", DIRECTOR_USER
        )


class TestUploadSignedDocument:
    def test_with_a_valid_pdf_returns_200(self, client, controller):
        controller.upload_signed_document.return_value = PLAN

        response = client.post(
            "/improvement-plans/1/documents/formato-1/signed",
            files={"file": ("firmado.pdf", b"%PDF-1.4 contenido", "application/pdf")},
        )

        assert response.status_code == 200
        controller.upload_signed_document.assert_awaited_once()

    def test_with_a_non_pdf_file_returns_400(self, client, controller):
        response = client.post(
            "/improvement-plans/1/documents/formato-1/signed",
            files={"file": ("firmado.docx", b"contenido", "application/msword")},
        )

        assert response.status_code == 400
        controller.upload_signed_document.assert_not_called()

    def test_with_an_empty_file_returns_400(self, client, controller):
        response = client.post(
            "/improvement-plans/1/documents/formato-1/signed",
            files={"file": ("firmado.pdf", b"", "application/pdf")},
        )

        assert response.status_code == 400
        controller.upload_signed_document.assert_not_called()


class TestDeleteSignedDocument:
    def test_returns_the_updated_plan(self, client, controller):
        controller.delete_signed_document.return_value = PLAN

        response = client.delete("/improvement-plans/1/documents/formato-1/signed")

        assert response.status_code == 200


class TestListEvidenceRequests:
    def test_returns_the_result(self, client, controller):
        controller.list_evidence_requests.return_value = [{"id": 1}]

        response = client.get("/improvement-plans/1/evidence-requests")

        assert response.status_code == 200


class TestCreateEvidenceRequest:
    def test_with_valid_payload_returns_201(self, client, controller):
        controller.create_evidence_request.return_value = {"id": 1, "title": "Rúbrica"}

        response = client.post(
            "/improvement-plans/1/evidence-requests", json={"title": "Rúbrica"}
        )

        assert response.status_code == 201

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.post(
            "/improvement-plans/1/evidence-requests", json={"title": "Rúbrica"}
        )

        assert response.status_code == 403


class TestGetEvidenceRequest:
    def test_returns_the_result(self, client, controller):
        controller.get_evidence_request.return_value = {"id": 5}

        response = client.get("/improvement-plans/1/evidence-requests/5")

        assert response.status_code == 200


class TestUpdateEvidenceRequest:
    def test_returns_the_updated_request(self, client, controller):
        controller.update_evidence_request.return_value = {"id": 5, "title": "Nuevo"}

        response = client.put(
            "/improvement-plans/1/evidence-requests/5", json={"title": "Nuevo"}
        )

        assert response.status_code == 200


class TestAddEvidenceComment:
    def test_open_to_a_teacher(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)
        controller.add_evidence_comment.return_value = {"id": 1, "body": "Listo"}

        response = client.post(
            "/improvement-plans/1/evidence-requests/5/comments",
            json={"body": "Listo"},
        )

        assert response.status_code == 201


class TestUploadEvidence:
    def test_with_a_valid_pdf_returns_201(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)
        controller.add_evidence.return_value = {"id": 1, "file_url": "/tmp/x.pdf"}

        with patch(
            "api.routes.improvement_plans.save_plan_evidence",
            return_value="/tmp/x.pdf",
        ):
            response = client.post(
                "/improvement-plans/1/evidences",
                files={"file": ("evidencia.pdf", b"%PDF-1.4 x", "application/pdf")},
                data={"description": "Rúbrica firmada"},
            )

        assert response.status_code == 201
        controller.add_evidence.assert_awaited_once()

    def test_with_a_non_pdf_file_returns_400(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.post(
            "/improvement-plans/1/evidences",
            files={"file": ("evidencia.txt", b"x", "text/plain")},
        )

        assert response.status_code == 400
        controller.add_evidence.assert_not_called()


class TestReviewEvidence:
    def test_returns_the_reviewed_evidence(self, client, controller):
        controller.review_evidence.return_value = {"id": 1, "status": "APROBADA"}

        response = client.put(
            "/improvement-plans/1/evidences/1/review", json={"status": "APROBADA"}
        )

        assert response.status_code == 200


class TestDeleteEvidence:
    def test_open_to_a_teacher(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.delete("/improvement-plans/1/evidences/1")

        assert response.status_code == 204
        controller.delete_evidence.assert_awaited_once_with(1, 1, DOCENTE_USER)


class TestDownloadEvidence:
    def test_streams_the_file(self, client, controller, tmp_path):
        pdf_path = tmp_path / "evidencia.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 contenido")
        controller.get_evidence_file.return_value = (str(pdf_path), "evidencia.pdf")

        response = client.get("/improvement-plans/1/evidences/1")

        assert response.status_code == 200


class TestDownloadDocumentWord:
    def test_returns_the_rendered_document(self, client, controller):
        controller.render_document_word.return_value = (b"contenido", "formato-1.doc")

        response = client.get("/improvement-plans/1/documents/formato-1/word")

        assert response.status_code == 200
        assert response.content == b"contenido"


class TestDownloadDocument:
    def test_streams_the_file(self, client, controller, tmp_path):
        pdf_path = tmp_path / "formato-1.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 contenido")
        controller.get_document_file.return_value = (str(pdf_path), "formato-1.pdf")

        response = client.get("/improvement-plans/1/documents/formato-1")

        assert response.status_code == 200
        controller.get_document_file.assert_awaited_once_with(
            1, "formato-1", DIRECTOR_USER, prefer_generated=False
        )
