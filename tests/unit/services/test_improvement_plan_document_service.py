"""
Unit tests for ImprovementPlanDocumentService.

Covers the part that carries real domain meaning: grouping plan items under the
five aspects of the official forms, and the acta signing lifecycle.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.exceptions import ResourceNotFoundError, ValidationError
from api.services.improvement_plan_document_service import (
    ImprovementPlanDocumentService,
    resolve_format_type,
)

ADMIN = {"id": 1, "roles": ["ADMIN"], "department_id": None}


def _plan(**overrides) -> dict:
    plan = {
        "id": 7,
        "teacher_id": 55,
        "department_id": 10,
        "teacher_name": "Docente de Prueba",
        "program_name": "Ingeniería de Sistemas",
        "acta_status": "BORRADOR",
        "items": [
            {"description": "Puntualidad", "commitment": "Llegar a tiempo", "aspect": 2,
             "comments": []},
            {"description": "Trato", "commitment": "Mejorar", "aspect": 5,
             "comments": [{"comment_id": 3, "original_text": "Llega tarde"}]},
            {"description": "Sin aspecto", "commitment": None, "aspect": None,
             "comments": []},
        ],
        "checkpoints": [
            {
                "stage": "PRIMER_SEGUIMIENTO",
                "scheduled_date": None,
                "aspect_notes": [{"aspect": 2, "note": "Mejoró"}],
            },
            {
                "stage": "SEGUNDO_SEGUIMIENTO",
                "scheduled_date": None,
                "aspect_notes": [{"aspect": 5, "note": "Sin quejas"}],
            },
        ],
        "courses": [{"course_name": "ESTRUCTURAS DE DATOS", "group_name": "B"}],
        "case_report": None,
    }
    plan.update(overrides)
    return plan


@pytest.fixture
def mock_documents_repository():
    repo = MagicMock()
    document = MagicMock()
    document.generated_pdf_url = "/uploads/improvement_plans/7/documents/f2.pdf"
    document.signed_pdf_url = None
    repo.get_by_format = MagicMock(return_value=document)
    repo.set_generated = MagicMock(return_value=(document, None))
    repo.set_signed = MagicMock(return_value=(document, None))
    return repo


@pytest.fixture
def mock_plans_repository():
    repo = MagicMock()
    repo.get_teacher_context = MagicMock(
        return_value={
            "code": "04041",
            "department_name": "Sistemas",
            "faculty_name": "Ingeniería",
        }
    )
    repo.set_acta_status = AsyncMock()
    return repo


@pytest.fixture
def mock_plan_service():
    service = MagicMock()
    service.get_by_id = AsyncMock(return_value=_plan())
    service.ensure_can_manage = MagicMock()
    return service


@pytest.fixture
def mock_audit_service():
    service = MagicMock()
    service.log = AsyncMock()
    return service


@pytest.fixture
def service(
    mock_documents_repository,
    mock_plans_repository,
    mock_plan_service,
    mock_audit_service,
):
    return ImprovementPlanDocumentService(
        mock_documents_repository,
        mock_plans_repository,
        mock_plan_service,
        mock_audit_service,
    )


class TestResolveFormatType:
    def test_accepts_the_three_slugs(self):
        assert resolve_format_type("formato-1") == "FORMATO_1"
        assert resolve_format_type("FORMATO-2") == "FORMATO_2"
        assert resolve_format_type("formato-3") == "FORMATO_3"

    def test_rejects_anything_else(self):
        with pytest.raises(ValidationError):
            resolve_format_type("formato-9")


class TestBuildContext:
    """Items are printed grouped under the five official aspects."""

    def test_groups_items_by_aspect(self, service):
        context = service.build_context(_plan())

        by_number = {a["aspect"]: a for a in context["aspects"]}

        assert len(context["aspects"]) == 5
        assert [i["description"] for i in by_number[2]["entries"]] == ["Puntualidad"]
        assert [i["description"] for i in by_number[5]["entries"]] == ["Trato"]
        # Aspects with nothing assigned still render, empty.
        assert by_number[1]["entries"] == []

    def test_items_without_aspect_are_not_printed(self, service):
        context = service.build_context(_plan())

        printed = [i["description"] for a in context["aspects"] for i in a["entries"]]

        assert "Sin aspecto" not in printed

    def test_cross_references_checkpoint_notes(self, service):
        context = service.build_context(_plan())

        by_number = {a["aspect"]: a for a in context["aspects"]}

        assert by_number[2]["first_note"] == "Mejoró"
        assert by_number[2]["second_note"] is None
        assert by_number[5]["second_note"] == "Sin quejas"

    def test_includes_the_form_header_data(self, service):
        context = service.build_context(_plan())

        assert context["teacher_code"] == "04041"
        assert context["department_name"] == "Sistemas"
        assert context["faculty_name"] == "Ingeniería"


class TestGenerate:
    async def test_renders_and_stores(self, service, mock_documents_repository):
        with patch(
            "api.services.improvement_plan_document_service.render_formato",
            return_value=b"%PDF-fake",
        ) as render, patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/x.pdf",
        ):
            await service.generate(7, "formato-2", ADMIN)

        render.assert_called_once()
        assert render.call_args[0][0] == "FORMATO_2"
        mock_documents_repository.set_generated.assert_called_once()

    async def test_removes_the_replaced_file(self, service, mock_documents_repository):
        mock_documents_repository.set_generated.return_value = (
            MagicMock(),
            "/uploads/old.pdf",
        )

        with patch(
            "api.services.improvement_plan_document_service.render_formato",
            return_value=b"%PDF",
        ), patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/new.pdf",
        ), patch(
            "api.services.improvement_plan_document_service.delete_plan_file"
        ) as delete:
            await service.generate(7, "formato-2", ADMIN)

        delete.assert_called_once_with("/uploads/old.pdf")


class TestUploadSigned:
    """The acta may only be signed after it has been closed."""

    async def test_rejects_signed_acta_while_draft(self, service, mock_plan_service):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="BORRADOR")

        with pytest.raises(ValidationError):
            await service.upload_signed(7, "formato-2", b"%PDF", ADMIN)

    async def test_closed_acta_becomes_signed(
        self, service, mock_plan_service, mock_plans_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="CERRADA")

        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/firmado.pdf",
        ):
            await service.upload_signed(7, "formato-2", b"%PDF", ADMIN)

        mock_plans_repository.set_acta_status.assert_awaited_once_with(7, "FIRMADA")

    async def test_other_formats_do_not_touch_the_acta(
        self, service, mock_plan_service, mock_plans_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="BORRADOR")

        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/f1.pdf",
        ):
            await service.upload_signed(7, "formato-1", b"%PDF", ADMIN)

        mock_plans_repository.set_acta_status.assert_not_awaited()


class TestGetFile:
    async def test_prefers_the_signed_copy(self, service, mock_documents_repository):
        mock_documents_repository.get_by_format.return_value.signed_pdf_url = "/s.pdf"

        filepath, filename = await service.get_file(7, "formato-2", ADMIN)

        assert filepath == "/s.pdf"
        assert filename == "formato-2_plan_7.pdf"

    async def test_can_force_the_generated_copy(
        self, service, mock_documents_repository
    ):
        mock_documents_repository.get_by_format.return_value.signed_pdf_url = "/s.pdf"

        filepath, _ = await service.get_file(
            7, "formato-2", ADMIN, prefer_generated=True
        )

        assert filepath.endswith("f2.pdf")

    async def test_raises_when_never_generated(
        self, service, mock_documents_repository
    ):
        mock_documents_repository.get_by_format.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.get_file(7, "formato-3", ADMIN)
