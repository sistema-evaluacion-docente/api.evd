"""Tests for ImprovementPlansController layer.

The controller is pure delegation to three services, plus one endpoint
(``update_checkpoint``) that chains a document refresh in between — that
ordering is the only thing worth asserting beyond the delegation itself.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.improvement_plans import ImprovementPlansController

USER = {"id": 2, "roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 7}


class TestImprovementPlansController:
    """Test suite for ImprovementPlansController."""

    @pytest.fixture
    def mock_service(self):
        """Mock ImprovementPlanService."""

        service = MagicMock()
        for name in (
            "get_all",
            "get_by_id",
            "get_my_plans",
            "get_candidates",
            "get_at_risk",
            "get_evaluated_periods",
            "get_history",
            "create",
            "update",
            "delete",
            "upsert_case_report",
            "update_checkpoint",
            "close_acta",
            "reopen_acta",
            "close",
            "get_teacher_courses",
        ):
            setattr(service, name, AsyncMock())
        service.get_threshold = MagicMock(return_value=3.5)
        return service

    @pytest.fixture
    def mock_document_service(self):
        """Mock ImprovementPlanDocumentService."""

        service = MagicMock()
        for name in (
            "generate",
            "render_word",
            "upload_signed",
            "delete_signed",
            "get_file",
            "refresh_followup_format",
        ):
            setattr(service, name, AsyncMock())
        return service

    @pytest.fixture
    def mock_evidence_service(self):
        """Mock ImprovementPlanEvidenceService."""

        service = MagicMock()
        for name in (
            "list_requests",
            "get_request",
            "create_request",
            "update_request",
            "add_comment",
            "add_evidence",
            "review_evidence",
            "delete_evidence",
            "get_evidence_file",
        ):
            setattr(service, name, AsyncMock())
        return service

    @pytest.fixture
    def controller(self, mock_service, mock_document_service, mock_evidence_service):
        """Create controller instance with mocked services."""

        return ImprovementPlansController(
            mock_service, mock_document_service, mock_evidence_service
        )

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_service(self, controller, mock_service):
        mock_service.get_all.return_value = {"items": []}

        result = await controller.get_all(USER, MagicMock(), teacher_id=3)

        assert result == {"items": []}

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        mock_service.get_by_id.return_value = {"id": 1}

        result = await controller.get_by_id(1, USER)

        assert result == {"id": 1}
        mock_service.get_by_id.assert_awaited_once_with(1, USER)

    @pytest.mark.asyncio
    async def test_get_my_plans_delegates_to_service(self, controller, mock_service):
        mock_service.get_my_plans.return_value = [{"id": 1}]

        result = await controller.get_my_plans(USER)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_candidates_delegates_to_service(self, controller, mock_service):
        mock_service.get_candidates.return_value = [{"teacher_id": 3}]

        result = await controller.get_candidates(USER, 1, 7)

        assert result == [{"teacher_id": 3}]

    @pytest.mark.asyncio
    async def test_get_at_risk_delegates_to_service(self, controller, mock_service):
        mock_service.get_at_risk.return_value = [{"teacher_id": 3}]

        result = await controller.get_at_risk(USER, 1, 7)

        assert result == [{"teacher_id": 3}]

    @pytest.mark.asyncio
    async def test_get_evaluated_periods_delegates_to_service(
        self, controller, mock_service
    ):
        mock_service.get_evaluated_periods.return_value = [{"id": 1}]

        result = await controller.get_evaluated_periods(USER, 7)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_indicators_builds_the_catalogue(self, controller, mock_service):
        result = await controller.get_indicators()

        assert result["threshold"] == 3.5
        assert "aspects" in result

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_service(self, controller, mock_service):
        mock_service.get_history.return_value = [{"plan_id": 1}]

        result = await controller.get_history(3, USER)

        assert result == [{"plan_id": 1}]

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        mock_service.create.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.create(payload, USER)

        assert result == {"id": 1}
        mock_service.create.assert_awaited_once_with(payload, USER)

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        mock_service.update.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.update(1, payload, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        await controller.delete(1, USER)

        mock_service.delete.assert_awaited_once_with(1, USER)

    @pytest.mark.asyncio
    async def test_upsert_case_report_delegates_to_service(
        self, controller, mock_service
    ):
        mock_service.upsert_case_report.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.upsert_case_report(1, payload, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_update_checkpoint_refreshes_the_document_then_returns_the_plan(
        self, controller, mock_service, mock_document_service
    ):
        """Test the checkpoint update, format refresh and re-fetch happen in order."""

        calls = []
        mock_service.update_checkpoint.side_effect = lambda *a, **k: calls.append(
            "update_checkpoint"
        )
        mock_document_service.refresh_followup_format.side_effect = (
            lambda *a, **k: calls.append("refresh")
        )
        mock_service.get_by_id.side_effect = lambda *a, **k: calls.append("get") or {
            "id": 1
        }
        payload = MagicMock()

        result = await controller.update_checkpoint(1, 5, payload, USER)

        assert result == {"id": 1}
        assert calls == ["update_checkpoint", "refresh", "get"]

    @pytest.mark.asyncio
    async def test_close_acta_delegates_to_service(self, controller, mock_service):
        mock_service.close_acta.return_value = {"id": 1}

        result = await controller.close_acta(1, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_reopen_acta_delegates_to_service(self, controller, mock_service):
        mock_service.reopen_acta.return_value = {"id": 1}

        result = await controller.reopen_acta(1, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_close_delegates_to_service(self, controller, mock_service):
        mock_service.close.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.close(1, payload, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_get_teacher_courses_delegates_to_service(
        self, controller, mock_service
    ):
        mock_service.get_teacher_courses.return_value = [{"course_code": "BD101"}]

        result = await controller.get_teacher_courses(3, 1, USER)

        assert result == [{"course_code": "BD101"}]

    @pytest.mark.asyncio
    async def test_generate_document_delegates_to_document_service(
        self, controller, mock_document_service
    ):
        mock_document_service.generate.return_value = {"id": 1}

        result = await controller.generate_document(1, "formato-1", USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_render_document_word_delegates_to_document_service(
        self, controller, mock_document_service
    ):
        mock_document_service.render_word.return_value = (b"x", "f.doc")

        result = await controller.render_document_word(1, "formato-1", USER)

        assert result == (b"x", "f.doc")

    @pytest.mark.asyncio
    async def test_upload_signed_document_delegates_to_document_service(
        self, controller, mock_document_service
    ):
        mock_document_service.upload_signed.return_value = {"id": 1}

        result = await controller.upload_signed_document(
            1, "formato-1", b"pdf", USER, filename="f.pdf"
        )

        assert result == {"id": 1}
        mock_document_service.upload_signed.assert_awaited_once_with(
            1, "formato-1", b"pdf", USER, filename="f.pdf"
        )

    @pytest.mark.asyncio
    async def test_delete_signed_document_delegates_to_document_service(
        self, controller, mock_document_service
    ):
        mock_document_service.delete_signed.return_value = {"id": 1}

        result = await controller.delete_signed_document(1, "formato-1", USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_get_document_file_delegates_to_document_service(
        self, controller, mock_document_service
    ):
        mock_document_service.get_file.return_value = ("/tmp/f.pdf", "f.pdf")

        result = await controller.get_document_file(
            1, "formato-1", USER, prefer_generated=True
        )

        assert result == ("/tmp/f.pdf", "f.pdf")
        mock_document_service.get_file.assert_awaited_once_with(
            1, "formato-1", USER, prefer_generated=True
        )

    @pytest.mark.asyncio
    async def test_list_evidence_requests_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.list_requests.return_value = [{"id": 1}]

        result = await controller.list_evidence_requests(1, USER)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_evidence_request_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.get_request.return_value = {"id": 5}

        result = await controller.get_evidence_request(1, 5, USER)

        assert result == {"id": 5}

    @pytest.mark.asyncio
    async def test_create_evidence_request_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.create_request.return_value = {"id": 5}
        payload = MagicMock()

        result = await controller.create_evidence_request(1, payload, USER)

        assert result == {"id": 5}

    @pytest.mark.asyncio
    async def test_update_evidence_request_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.update_request.return_value = {"id": 5}
        payload = MagicMock()

        result = await controller.update_evidence_request(1, 5, payload, USER)

        assert result == {"id": 5}

    @pytest.mark.asyncio
    async def test_add_evidence_comment_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.add_comment.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.add_evidence_comment(1, 5, payload, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_add_evidence_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.add_evidence.return_value = {"id": 1}

        result = await controller.add_evidence(
            1, "/tmp/f.pdf", USER, description="desc", item_id=2, request_id=5
        )

        assert result == {"id": 1}
        mock_evidence_service.add_evidence.assert_awaited_once_with(
            1, "/tmp/f.pdf", USER, description="desc", item_id=2, request_id=5
        )

    @pytest.mark.asyncio
    async def test_review_evidence_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.review_evidence.return_value = {"id": 1}
        payload = MagicMock()

        result = await controller.review_evidence(1, 1, payload, USER)

        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_delete_evidence_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        await controller.delete_evidence(1, 1, USER)

        mock_evidence_service.delete_evidence.assert_awaited_once_with(1, 1, USER)

    @pytest.mark.asyncio
    async def test_get_evidence_file_delegates_to_evidence_service(
        self, controller, mock_evidence_service
    ):
        mock_evidence_service.get_evidence_file.return_value = ("/tmp/e.pdf", "e.pdf")

        result = await controller.get_evidence_file(1, 1, USER)

        assert result == ("/tmp/e.pdf", "e.pdf")
