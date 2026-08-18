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


@pytest.fixture
def mock_plans_repository():
    repo = MagicMock()
    repo.get_teacher_user_id = MagicMock(return_value=TEACHER_USER_ID)
    repo.get_department_director_user_id = MagicMock(return_value=DIRECTOR_USER_ID)
    return repo


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
        # The app routes are Spanish; a link the SPA cannot resolve is a
        # notification that opens on a 404.
        assert notification.link == "/planes/7"

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
