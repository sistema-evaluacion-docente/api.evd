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
DIRECTOR = {"id": 2, "roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 10}


def _plan(**overrides) -> dict:
    plan = {
        "id": 7,
        "title": "Plan de mejoramiento 2025-1",
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


TEACHER_CONTACT = {"user_id": 4, "name": "Ada Lovelace", "email": "ada@ufps.edu.co"}


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    service.create = AsyncMock()
    return service


@pytest.fixture
def sent_email():
    """Every message the service hands to the transport, without sending any."""

    with patch(
        "api.services.improvement_plan_document_service.send_email"
    ) as send:
        yield send


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
    repo.get_teacher_contact = MagicMock(
        return_value=dict(TEACHER_CONTACT)
    )
    repo.get_department_context = MagicMock(
        return_value={"department_name": "Sistemas"}
    )
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
    mock_notification_service,
):
    return ImprovementPlanDocumentService(
        mock_documents_repository,
        mock_plans_repository,
        mock_plan_service,
        mock_audit_service,
        mock_notification_service,
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
    """Signing the acta is what settles it: there is no separate closing step."""

    async def test_draft_acta_becomes_signed(
        self, service, mock_plan_service, mock_plans_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="BORRADOR")

        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/firmado.pdf",
        ):
            await service.upload_signed(7, "formato-2", b"%PDF", ADMIN)

        mock_plans_repository.set_acta_status.assert_awaited_once_with(
            7, "FIRMADA", closed_by=1
        )

    async def test_checks_the_acta_is_filled_in_before_signing_it(
        self, service, mock_plan_service
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="BORRADOR")
        mock_plan_service.ensure_acta_complete.side_effect = ValidationError("falta el acta")

        with pytest.raises(ValidationError):
            await service.upload_signed(7, "formato-2", b"%PDF", ADMIN)

    async def test_only_the_acta_is_checked_for_completeness(
        self, service, mock_plan_service
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="BORRADOR")

        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/f1.pdf",
        ):
            await service.upload_signed(7, "formato-1", b"%PDF", ADMIN)

        mock_plan_service.ensure_acta_complete.assert_not_called()

    async def test_closed_acta_becomes_signed(
        self, service, mock_plan_service, mock_plans_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="CERRADA")

        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/firmado.pdf",
        ):
            await service.upload_signed(7, "formato-2", b"%PDF", ADMIN)

        mock_plans_repository.set_acta_status.assert_awaited_once_with(
            7, "FIRMADA", closed_by=1
        )

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

    async def test_renders_it_when_never_generated(
        self, service, mock_documents_repository
    ):
        """There is no "generar" step in the interface any more: asking for the
        file is what produces it."""

        mock_documents_repository.get_by_format.return_value = None

        with patch(
            "api.services.improvement_plan_document_service.render_formato",
            return_value=b"%PDF",
        ) as render, patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/fresh.pdf",
        ):
            filepath, _ = await service.get_file(7, "formato-3", ADMIN)

        render.assert_called_once()
        assert filepath == "/uploads/fresh.pdf"
        mock_documents_repository.set_generated.assert_called_once()


class TestDeleteSigned:
    """The escape hatch for a scan attached by mistake."""

    async def test_drops_the_file_and_the_row(
        self, service, mock_documents_repository
    ):
        mock_documents_repository.clear_signed.return_value = "/uploads/firmado.pdf"

        with patch(
            "api.services.improvement_plan_document_service.delete_plan_file"
        ) as delete:
            await service.delete_signed(7, "formato-3", ADMIN)

        mock_documents_repository.clear_signed.assert_called_once_with(7, "FORMATO_3")
        delete.assert_called_once_with("/uploads/firmado.pdf")

    async def test_raises_when_nothing_was_signed(
        self, service, mock_documents_repository
    ):
        mock_documents_repository.clear_signed.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.delete_signed(7, "formato-2", ADMIN)

    async def test_signed_acta_walks_back_to_draft(
        self, service, mock_plan_service, mock_documents_repository, mock_plans_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="FIRMADA")
        mock_documents_repository.clear_signed.return_value = "/uploads/acta.pdf"

        with patch("api.services.improvement_plan_document_service.delete_plan_file"):
            await service.delete_signed(7, "formato-2", DIRECTOR)

        # Back to BORRADOR, not merely CERRADA: taking the signature off is what
        # makes the agreement editable again.
        mock_plans_repository.set_acta_status.assert_awaited_once_with(7, "BORRADOR")

    async def test_only_the_owning_director_unsigns_the_acta(
        self, service, mock_plan_service, mock_documents_repository
    ):
        mock_plan_service.get_by_id.return_value = _plan(acta_status="FIRMADA")
        mock_documents_repository.clear_signed.return_value = "/uploads/acta.pdf"

        with patch("api.services.improvement_plan_document_service.delete_plan_file"):
            await service.delete_signed(7, "formato-2", DIRECTOR)

        mock_plan_service.ensure_is_department_director.assert_called_once()
        mock_plan_service.ensure_can_manage.assert_not_called()

    async def test_the_other_formats_stay_open_to_any_manager(
        self, service, mock_plan_service, mock_documents_repository
    ):
        mock_documents_repository.clear_signed.return_value = "/uploads/f3.pdf"

        with patch("api.services.improvement_plan_document_service.delete_plan_file"):
            await service.delete_signed(7, "formato-3", ADMIN)

        mock_plan_service.ensure_can_manage.assert_called_once()
        mock_plan_service.ensure_is_department_director.assert_not_called()


class TestRefreshFollowupFormat:
    """Formato 3 is the follow-up matrix, so recording a seguimiento redraws it."""

    async def test_rerenders_formato_3(self, service, mock_documents_repository):
        with patch(
            "api.services.improvement_plan_document_service.render_formato",
            return_value=b"%PDF",
        ) as render, patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/f3.pdf",
        ), patch("api.services.improvement_plan_document_service.delete_plan_file"):
            await service.refresh_followup_format(7, ADMIN)

        assert render.call_args[0][0] == "FORMATO_3"
        mock_documents_repository.set_generated.assert_called_once()

    async def test_invalidates_the_previous_signature(
        self, service, mock_documents_repository
    ):
        """The signatures were collected over a page that no longer matches."""

        mock_documents_repository.clear_signed.return_value = "/uploads/firmado.pdf"

        with patch(
            "api.services.improvement_plan_document_service.render_formato",
            return_value=b"%PDF",
        ), patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/f3.pdf",
        ), patch(
            "api.services.improvement_plan_document_service.delete_plan_file"
        ) as delete:
            await service.refresh_followup_format(7, ADMIN)

        mock_documents_repository.clear_signed.assert_called_once_with(7, "FORMATO_3")
        delete.assert_any_call("/uploads/firmado.pdf")


class TestTellingTheTeacherItIsSigned:
    """The signed scan is what the agreement actually is, so it is announced.

    Before this the document simply turned up on the teacher's page one day: the
    bell said nothing, and nothing on their side gave them a reason to look.
    """

    async def _sign(self, service, slug="formato-2", actor=ADMIN):
        with patch(
            "api.services.improvement_plan_document_service.save_plan_document",
            return_value="/uploads/firmado.pdf",
        ):
            await service.upload_signed(7, slug, b"%PDF", actor)

    async def test_the_bell_says_which_form_was_signed(
        self, service, mock_notification_service, sent_email
    ):
        await self._sign(service)

        notification = mock_notification_service.create.call_args[0][0]
        assert notification.user_id == TEACHER_CONTACT["user_id"]
        assert notification.title == "Formato 2 firmado"
        # The teacher's own route; /planes/{id} is the director's screen.
        assert notification.link == "/mis-planes/7"

    async def test_the_same_goes_out_by_email(
        self, service, mock_notification_service, sent_email
    ):
        await self._sign(service)

        message = sent_email.call_args[0][0]
        assert message.to == TEACHER_CONTACT["email"]
        assert "Formato 2" in message.subject
        assert "/mis-planes/7" in message.text

    async def test_the_seguimiento_is_announced_too(
        self, service, mock_notification_service, sent_email
    ):
        await self._sign(service, slug="formato-3")

        assert mock_notification_service.create.call_args[0][0].title == "Formato 3 firmado"

    async def test_the_caso_reportado_is_not(
        self, service, mock_notification_service, sent_email
    ):
        # Formato 1 is what the academic programme sent the department head:
        # internal to them, and not the teacher's to be told about.
        await self._sign(service, slug="formato-1")

        mock_notification_service.create.assert_not_awaited()
        sent_email.assert_not_called()

    async def test_a_teacher_with_no_account_is_simply_skipped(
        self, service, mock_plans_repository, mock_notification_service, sent_email
    ):
        mock_plans_repository.get_teacher_contact.return_value = None

        await self._sign(service)

        mock_notification_service.create.assert_not_awaited()
        sent_email.assert_not_called()

    async def test_a_mail_server_that_is_down_does_not_undo_the_upload(
        self, service, mock_documents_repository, sent_email
    ):
        sent_email.side_effect = OSError("connection refused")

        await self._sign(service)

        # The scan is already stored and audited by the time the notice goes.
        mock_documents_repository.set_signed.assert_called_once()
