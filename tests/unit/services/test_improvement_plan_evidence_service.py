"""
Unit tests for ImprovementPlanEvidenceService.

The interesting behaviour is the request state machine: submitting puts the
request in the director's court, a rejection reopens it for a new attempt, and
each transition notifies the other party.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.exceptions import ResourceNotFoundError, ValidationError
from api.schemas.improvement_plan import (
    EvidenceStatus,
    ImprovementPlanEvidenceCommentCreate,
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceReview,
)
from api.services.improvement_plan_evidence_service import (
    ImprovementPlanEvidenceService,
)

DIRECTOR = {"id": 2, "roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 10}
TEACHER = {"id": 4, "roles": ["DOCENTE"], "department_id": 10}

TEACHER_USER_ID = TEACHER["id"]
DIRECTOR_USER_ID = DIRECTOR["id"]


def _plan(**overrides) -> dict:
    plan = {
        "id": 7,
        "title": "Plan de mejoramiento 2025-1",
        "teacher_id": 55,
        "department_id": 10,
        "status": "EN_SEGUIMIENTO",
        "items": [{"id": 31}],
    }
    plan.update(overrides)
    return plan


@pytest.fixture
def mock_evidences_repository():
    repo = MagicMock()
    repo.get_request = MagicMock(return_value=MagicMock(id=9))
    repo.create_request = AsyncMock(return_value={"id": 9, "title": "Listas"})
    repo.update_request = AsyncMock(return_value={"id": 9})
    repo.add_comment = AsyncMock(return_value={"id": 3, "body": "ok"})
    repo.add_evidence = AsyncMock(return_value={"id": 5})
    repo.review_evidence = AsyncMock(return_value={"id": 5, "status": "APROBADA"})
    repo.delete_evidence = AsyncMock(return_value="/uploads/e.pdf")
    repo.set_request_status = MagicMock()
    evidence = MagicMock()
    evidence.id = 5
    evidence.request_id = 9
    evidence.uploaded_by = TEACHER_USER_ID
    evidence.file_url = "/uploads/e.pdf"
    repo.get_evidence = MagicMock(return_value=evidence)
    return repo


TEACHER_CONTACT = {
    "user_id": TEACHER_USER_ID,
    "name": "Ada Lovelace",
    "email": "ada@ufps.edu.co",
}
DIRECTOR_CONTACT = {
    "user_id": DIRECTOR_USER_ID,
    "name": "Orlando Beltrán",
    "email": "orlando@ufps.edu.co",
}


@pytest.fixture
def mock_plans_repository():
    repo = MagicMock()
    repo.get_teacher_user_id = MagicMock(return_value=TEACHER_USER_ID)
    repo.get_department_director_user_id = MagicMock(return_value=DIRECTOR_USER_ID)
    repo.get_teacher_contact = MagicMock(return_value=dict(TEACHER_CONTACT))
    repo.get_department_director_contact = MagicMock(
        return_value=dict(DIRECTOR_CONTACT)
    )
    repo.get_department_context = MagicMock(
        return_value={"department_name": "Departamento de Sistemas"}
    )
    return repo


@pytest.fixture
def sent_email():
    """Every message the loop hands to the transport, without sending any.

    Patched at the service, not at `email_sender`, because the service dispatches
    it through `asyncio.to_thread` — the calls have to be recorded on the object
    the service actually holds.
    """

    with patch(
        "api.services.improvement_plan_evidence_service.send_email"
    ) as send:
        yield send


@pytest.fixture
def mock_plan_service():
    service = MagicMock()
    service.get_by_id = AsyncMock(return_value=_plan())
    service.ensure_can_manage = MagicMock()
    return service


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    service.create = AsyncMock()
    return service


@pytest.fixture
def mock_audit_service():
    service = MagicMock()
    service.log = AsyncMock()
    return service


@pytest.fixture
def service(
    mock_evidences_repository,
    mock_plans_repository,
    mock_plan_service,
    mock_notification_service,
    mock_audit_service,
):
    return ImprovementPlanEvidenceService(
        mock_evidences_repository,
        mock_plans_repository,
        mock_plan_service,
        mock_notification_service,
        mock_audit_service,
    )


class TestCreateRequest:
    async def test_creates_and_notifies_the_teacher(
        self, service, mock_evidences_repository, mock_notification_service
    ):
        payload = ImprovementPlanEvidenceRequestCreate(title="Listas de asistencia")

        await service.create_request(7, payload, DIRECTOR)

        mock_evidences_repository.create_request.assert_awaited_once()
        notification = mock_notification_service.create.call_args[0][0]
        assert notification.user_id == TEACHER_USER_ID
        # The teacher's own route. /planes/{id} is the director's screen, which
        # answers a teacher with a page they have no business on.
        assert notification.link == "/mis-planes/7"

    async def test_rejected_on_a_closed_plan(self, service, mock_plan_service):
        mock_plan_service.get_by_id.return_value = _plan(status="CERRADO_CUMPLIDO")

        with pytest.raises(ValidationError):
            await service.create_request(
                7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
            )


class TestSubmitEvidence:
    """A submission moves the request into the director's court."""

    async def test_submission_sets_the_request_in_review(
        self, service, mock_evidences_repository
    ):
        await service.add_evidence(7, "/uploads/e.pdf", TEACHER, request_id=9)

        mock_evidences_repository.set_request_status.assert_called_once_with(
            9, "EN_REVISION"
        )

    async def test_teacher_submission_notifies_the_director(
        self, service, mock_notification_service
    ):
        await service.add_evidence(7, "/uploads/e.pdf", TEACHER, request_id=9)

        notification = mock_notification_service.create.call_args[0][0]
        assert notification.user_id == DIRECTOR_USER_ID

    async def test_rejects_an_item_from_another_plan(self, service):
        with pytest.raises(ValidationError):
            await service.add_evidence(7, "/uploads/e.pdf", TEACHER, item_id=999)

    async def test_rejects_an_unknown_request(
        self, service, mock_evidences_repository
    ):
        mock_evidences_repository.get_request.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.add_evidence(7, "/uploads/e.pdf", TEACHER, request_id=404)

    async def test_free_evidence_does_not_touch_any_request(
        self, service, mock_evidences_repository
    ):
        await service.add_evidence(7, "/uploads/e.pdf", TEACHER)

        mock_evidences_repository.set_request_status.assert_not_called()


class TestReviewEvidence:
    async def test_approval_closes_the_request(
        self, service, mock_evidences_repository
    ):
        await service.review_evidence(
            7, 5, ImprovementPlanEvidenceReview(status=EvidenceStatus.APROBADA), DIRECTOR
        )

        mock_evidences_repository.set_request_status.assert_called_once_with(
            9, "APROBADA"
        )

    async def test_rejection_reopens_the_request_with_a_system_note(
        self, service, mock_evidences_repository
    ):
        await service.review_evidence(
            7,
            5,
            ImprovementPlanEvidenceReview(status=EvidenceStatus.RECHAZADA),
            DIRECTOR,
        )

        mock_evidences_repository.set_request_status.assert_called_once_with(
            9, "PENDIENTE"
        )
        system_comments = [
            call
            for call in mock_evidences_repository.add_comment.await_args_list
            if call.kwargs.get("is_system")
        ]
        assert len(system_comments) == 1

    async def test_review_notifies_the_teacher(
        self, service, mock_notification_service
    ):
        await service.review_evidence(
            7,
            5,
            ImprovementPlanEvidenceReview(
                status=EvidenceStatus.RECHAZADA, comment="Falta la firma"
            ),
            DIRECTOR,
        )

        notification = mock_notification_service.create.call_args[0][0]
        assert notification.user_id == TEACHER_USER_ID
        assert notification.message == "Falta la firma"

    async def test_raises_for_an_unknown_evidence(
        self, service, mock_evidences_repository
    ):
        mock_evidences_repository.get_evidence.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.review_evidence(
                7,
                5,
                ImprovementPlanEvidenceReview(status=EvidenceStatus.APROBADA),
                DIRECTOR,
            )


class TestComments:
    async def test_teacher_comment_notifies_the_director(
        self, service, mock_notification_service
    ):
        await service.add_comment(
            7, 9, ImprovementPlanEvidenceCommentCreate(body="Ya subí el archivo"), TEACHER
        )

        assert mock_notification_service.create.call_args[0][0].user_id == DIRECTOR_USER_ID

    async def test_director_comment_notifies_the_teacher(
        self, service, mock_notification_service
    ):
        await service.add_comment(
            7, 9, ImprovementPlanEvidenceCommentCreate(body="Falta la firma"), DIRECTOR
        )

        assert mock_notification_service.create.call_args[0][0].user_id == TEACHER_USER_ID


class TestDeleteEvidence:
    async def test_uploader_may_delete_without_being_a_manager(
        self, service, mock_plan_service
    ):
        with patch(
            "api.services.improvement_plan_evidence_service.delete_plan_file"
        ) as delete_file:
            await service.delete_evidence(7, 5, TEACHER)

        mock_plan_service.ensure_can_manage.assert_not_called()
        delete_file.assert_called_once_with("/uploads/e.pdf")

    async def test_non_uploader_must_be_a_manager(self, service, mock_plan_service):
        other_teacher = {"id": 99, "roles": ["DOCENTE"], "department_id": 10}

        with patch("api.services.improvement_plan_evidence_service.delete_plan_file"):
            await service.delete_evidence(7, 5, other_teacher)

        mock_plan_service.ensure_can_manage.assert_called_once()


class TestNotificationLinks:
    """Each side of the loop reads the plan on its own screen.

    Both roles are notified about the same plan, and the two views are different
    routes: sending everyone to the director's one is how a teacher ends up on a
    screen they cannot open.
    """

    async def test_the_teacher_is_sent_to_their_own_view(
        self, service, mock_notification_service
    ):
        await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        notification = mock_notification_service.create.call_args[0][0]

        assert notification.user_id == TEACHER_USER_ID
        assert notification.link == "/mis-planes/7"

    async def test_the_director_is_sent_to_the_management_view(
        self, service, mock_notification_service
    ):
        await service.add_comment(
            7,
            1,
            ImprovementPlanEvidenceCommentCreate(body="Ya la subí"),
            TEACHER,
        )

        notification = mock_notification_service.create.call_args[0][0]

        assert notification.user_id == DIRECTOR_USER_ID
        assert notification.link == "/planes/7"

    async def test_a_review_takes_the_teacher_to_their_own_view(
        self, service, mock_notification_service
    ):
        await service.review_evidence(
            7, 3, ImprovementPlanEvidenceReview(status=EvidenceStatus.APROBADA), DIRECTOR
        )

        notification = mock_notification_service.create.call_args[0][0]

        assert notification.link == "/mis-planes/7"

    async def test_an_account_on_both_sides_still_hears_the_bell(
        self, service, mock_notification_service, mock_plans_repository
    ):
        # A director with a plan on themselves: the notice used to be dropped
        # because the recipient was the one who acted, so the plan showed no
        # sign of the request that had just been made on it.
        mock_plans_repository.get_teacher_user_id.return_value = DIRECTOR_USER_ID

        await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        notification = mock_notification_service.create.call_args[0][0]

        assert notification.user_id == DIRECTOR_USER_ID
        assert notification.link == "/mis-planes/7"


class TestEmail:
    """The inbox half of the loop.

    The bell only reaches someone already on the site, and both sides of this
    loop are waiting on the other: a deliverable has a deadline, and a review is
    what unblocks the teacher's next attempt.
    """

    async def test_a_requested_deliverable_reaches_the_teacher(
        self, service, sent_email
    ):
        payload = ImprovementPlanEvidenceRequestCreate(
            title="Listas de asistencia", description="Semanas 1 a 8"
        )

        await service.create_request(7, payload, DIRECTOR)

        sent_email.assert_called_once()
        message = sent_email.call_args[0][0]
        assert message.to == TEACHER_CONTACT["email"]
        assert "Listas de asistencia" in message.text
        # The teacher's own screen, same as the notification's link.
        assert "/mis-planes/7" in message.text

    async def test_a_submission_reaches_the_director(self, service, sent_email):
        await service.add_evidence(7, "/uploads/e.pdf", TEACHER, request_id=9)

        message = sent_email.call_args[0][0]
        assert message.to == DIRECTOR_CONTACT["email"]
        # The screen a plan is managed from, which is where the review happens.
        assert "/planes/7" in message.text

    async def test_a_review_tells_the_teacher_how_it_went(self, service, sent_email):
        await service.review_evidence(
            7,
            5,
            ImprovementPlanEvidenceReview(
                status=EvidenceStatus.RECHAZADA, comment="Falta la firma"
            ),
            DIRECTOR,
        )

        message = sent_email.call_args[0][0]
        assert message.to == TEACHER_CONTACT["email"]
        assert "rechazada" in message.subject.lower()
        assert "Falta la firma" in message.text

    async def test_an_approval_says_so_instead(self, service, sent_email):
        await service.review_evidence(
            7, 5, ImprovementPlanEvidenceReview(status=EvidenceStatus.APROBADA), DIRECTOR
        )

        assert "aprobada" in sent_email.call_args[0][0].subject.lower()

    async def test_each_comment_reaches_the_other_side(self, service, sent_email):
        comment = ImprovementPlanEvidenceCommentCreate(body="¿Sirve así?")

        await service.add_comment(7, 9, comment, TEACHER)
        assert sent_email.call_args[0][0].to == DIRECTOR_CONTACT["email"]

        await service.add_comment(7, 9, comment, DIRECTOR)
        assert sent_email.call_args[0][0].to == TEACHER_CONTACT["email"]

    async def test_an_account_on_both_sides_is_written_to_all_the_same(
        self, service, sent_email, mock_plans_repository
    ):
        # The director requesting a deliverable *is* the plan's teacher — one
        # account holding both roles, which is how the loop gets tested end to
        # end. Dropping the mail there is what left that plan silent.
        mock_plans_repository.get_teacher_contact.return_value = {
            **TEACHER_CONTACT,
            "user_id": DIRECTOR["id"],
        }

        await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        sent_email.assert_called_once()
        assert sent_email.call_args[0][0].to == TEACHER_CONTACT["email"]

    async def test_a_teacher_with_no_account_is_simply_skipped(
        self, service, sent_email, mock_plans_repository
    ):
        # Teachers imported from an evaluation and never signed in have no user
        # behind them, so there is nowhere to write to.
        mock_plans_repository.get_teacher_contact.return_value = None

        await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        sent_email.assert_not_called()

    async def test_a_contact_with_no_address_is_skipped_too(
        self, service, sent_email, mock_plans_repository
    ):
        mock_plans_repository.get_teacher_contact.return_value = {
            **TEACHER_CONTACT,
            "email": None,
        }

        await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        sent_email.assert_not_called()

    async def test_a_mail_server_that_is_down_does_not_undo_the_request(
        self, service, sent_email, mock_evidences_repository
    ):
        sent_email.side_effect = OSError("connection refused")

        request = await service.create_request(
            7, ImprovementPlanEvidenceRequestCreate(title="Listas"), DIRECTOR
        )

        # The evidence is already stored and audited by the time the mail goes.
        assert request == {"id": 9, "title": "Listas"}
        mock_evidences_repository.create_request.assert_awaited_once()
