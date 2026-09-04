"""
Unit tests for ImprovementPlanService.

Focus on the business rules the official UFPS forms impose: who may see or touch
a plan, the duplicate-plan guard, and the acta lock.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.exceptions import (
    PermissionDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.schemas.improvement_plan import (
    CloseResult,
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanClose,
    ImprovementPlanCreate,
    ImprovementPlanUpdate,
)
from api.services.improvement_plan_service import ImprovementPlanService

ADMIN = {"id": 1, "roles": ["ADMIN"], "department_id": None}
DIRECTOR = {"id": 2, "roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 10}
OTHER_DIRECTOR = {"id": 3, "roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 99}
TEACHER = {"id": 4, "roles": ["DOCENTE"], "department_id": 10}


def _plan(**overrides) -> dict:
    plan = {
        "id": 7,
        "teacher_id": 55,
        "department_id": 10,
        "title": "Plan de prueba",
        "acta_status": "BORRADOR",
        "acta_number": None,
        "acta_date": None,
        "items": [],
    }
    plan.update(overrides)
    return plan


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=_plan())
    repo.has_plan_for = AsyncMock(return_value=False)
    repo.create = AsyncMock(return_value=_plan())
    repo.update = AsyncMock(return_value=_plan(title="Actualizado"))
    repo.set_acta_status = AsyncMock(return_value=_plan(acta_status="CERRADA"))
    repo.get_teacher_user_id = MagicMock(return_value=TEACHER["id"])
    repo.delete = AsyncMock(return_value=True)
    repo.get_teacher_contact = MagicMock(
        return_value={
            "user_id": TEACHER["id"],
            "name": "Ada Lovelace",
            "email": "ada@ufps.edu.co",
        }
    )
    repo.get_department_context = MagicMock(
        return_value={
            "department_name": "Departamento de Sistemas",
            "faculty_name": "Ingeniería",
        }
    )
    return repo


@pytest.fixture
def mock_settings_repository():
    repo = MagicMock()
    setting = MagicMock()
    setting.value = "3.5"
    repo.get_by_key = MagicMock(return_value=setting)
    return repo


@pytest.fixture
def mock_audit_service():
    service = MagicMock()
    service.log = AsyncMock()
    return service


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    service.create = AsyncMock()
    return service


@pytest.fixture
def service(
    mock_repository,
    mock_settings_repository,
    mock_audit_service,
    mock_notification_service,
):
    return ImprovementPlanService(
        mock_repository,
        mock_settings_repository,
        mock_audit_service,
        mock_notification_service,
    )


class TestThreshold:
    """The institutional threshold comes from the settings table."""

    def test_reads_the_setting(self, service):
        assert service.get_threshold() == 3.5

    def test_falls_back_when_missing(self, service, mock_settings_repository):
        mock_settings_repository.get_by_key.return_value = None

        assert service.get_threshold() == 3.5

    def test_falls_back_when_not_a_number(self, service, mock_settings_repository):
        mock_settings_repository.get_by_key.return_value.value = "no-es-un-numero"

        assert service.get_threshold() == 3.5


class TestDepartmentScope:
    """Listings may span departments for an ADMIN; aggregations may not."""

    def test_admin_without_department_lists_across_departments(self, service):
        assert service.department_filter(ADMIN, None) is None

    def test_admin_who_directs_a_department_falls_back_to_it(self, service):
        """An admin that also directs a department shouldn't have to name it."""

        admin_director = {"id": 9, "roles": ["ADMIN", "DIRECTOR DE DEPARTAMENTO"], "department_id": 2}

        assert service.department_filter(admin_director, None) == 2
        assert service.require_department_id(admin_director, None) == 2

    def test_admin_can_still_target_another_department(self, service):
        admin_director = {"id": 9, "roles": ["ADMIN"], "department_id": 2}

        assert service.department_filter(admin_director, 7) == 7

    def test_director_is_pinned_to_their_own(self, service):
        assert service.department_filter(DIRECTOR, 99) == 10

    def test_director_without_department_is_rejected(self, service):
        with pytest.raises(ValidationError):
            service.department_filter({"id": 5, "roles": ["DIRECTOR DE DEPARTAMENTO"]}, None)

    def test_aggregations_require_an_explicit_department_for_admin(self, service):
        with pytest.raises(ValidationError):
            service.require_department_id(ADMIN, None)

    def test_aggregations_accept_an_explicit_department(self, service):
        assert service.require_department_id(ADMIN, 42) == 42


class TestAccessControl:
    """ADMIN sees all, directors their department, teachers only their own plan."""

    def test_admin_can_access(self, service):
        service.ensure_can_access(ADMIN, _plan())

    def test_director_of_the_department_can_access(self, service):
        service.ensure_can_access(DIRECTOR, _plan())

    def test_director_of_another_department_cannot(self, service):
        with pytest.raises(PermissionDeniedError):
            service.ensure_can_access(OTHER_DIRECTOR, _plan())

    def test_owner_teacher_can_access(self, service, mock_repository):
        mock_repository.get_teacher_user_id.return_value = TEACHER["id"]

        service.ensure_can_access(TEACHER, _plan())

    def test_other_teacher_cannot_access(self, service, mock_repository):
        mock_repository.get_teacher_user_id.return_value = 999

        with pytest.raises(PermissionDeniedError):
            service.ensure_can_access(TEACHER, _plan())

    def test_teacher_cannot_manage_their_own_plan(self, service):
        with pytest.raises(PermissionDeniedError):
            service.ensure_can_manage(TEACHER, _plan())


class TestUnsigningTheActaIsTheDirectors:
    """Taking the signature off reopens the agreement, so it is not an ADMIN's."""

    def test_the_owning_director_can(self, service):
        service.ensure_is_department_director(DIRECTOR, _plan())

    def test_an_admin_cannot(self, service):
        with pytest.raises(PermissionDeniedError):
            service.ensure_is_department_director(ADMIN, _plan())

    def test_a_director_of_another_department_cannot(self, service):
        with pytest.raises(PermissionDeniedError):
            service.ensure_is_department_director(OTHER_DIRECTOR, _plan())

    def test_the_teacher_cannot(self, service):
        with pytest.raises(PermissionDeniedError):
            service.ensure_is_department_director(TEACHER, _plan())


class TestActaCompleteness:
    """An acta cannot be frozen — by closing or by signing — while it is blank."""

    def test_requires_a_number_and_a_date(self, service):
        with pytest.raises(ValidationError):
            service.ensure_acta_complete(_plan(items=[{"commitment": "Llegar a tiempo"}]))

    def test_requires_at_least_one_commitment(self, service):
        with pytest.raises(ValidationError):
            service.ensure_acta_complete(
                _plan(acta_number="042", acta_date="2026-08-12", items=[{"commitment": None}])
            )

    def test_passes_when_the_acta_is_filled_in(self, service):
        service.ensure_acta_complete(
            _plan(
                acta_number="042",
                acta_date="2026-08-12",
                items=[{"commitment": "Llegar a tiempo"}],
            )
        )


class TestGetById:
    async def test_returns_the_plan(self, service):
        assert (await service.get_by_id(7, ADMIN))["id"] == 7

    async def test_raises_when_missing(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.get_by_id(7, ADMIN)


class TestCreate:
    """A teacher may only have one plan per origin period."""

    def _payload(self) -> ImprovementPlanCreate:
        return ImprovementPlanCreate(
            teacher_id=55, origin_period_id=3, title="Plan de prueba"
        )

    async def test_creates_and_audits(self, service, mock_repository, mock_audit_service):
        plan = await service.create(self._payload(), ADMIN)

        assert plan["id"] == 7
        mock_repository.create.assert_awaited_once()
        mock_audit_service.log.assert_awaited_once()

    async def test_rejects_a_duplicate(self, service, mock_repository):
        mock_repository.has_plan_for.return_value = True

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(self._payload(), ADMIN)

        mock_repository.create.assert_not_awaited()


class TestAnnounceNewPlan:
    """Creating a plan is the moment the teacher has to hear about it.

    Everything here is best-effort: the plan is already created and audited by
    the time the announcement runs, so nothing it does may turn a successful
    creation into a failed request.
    """

    def _payload(self) -> ImprovementPlanCreate:
        return ImprovementPlanCreate(
            teacher_id=55, origin_period_id=3, title="Plan de prueba"
        )

    async def test_emails_the_teacher(self, service):
        with patch(
            "api.services.improvement_plan_service.send_email"
        ) as send:
            await service.create(self._payload(), DIRECTOR)

        (message,) = send.call_args.args

        assert message.to == "ada@ufps.edu.co"
        assert "/mis-planes/7" in message.html

    async def test_signs_the_mail_as_the_director_who_created_it(self, service):
        with patch("api.services.improvement_plan_service.send_email") as send:
            await service.create(self._payload(), {**DIRECTOR, "name": "Marco Adarme"})

        (message,) = send.call_args.args

        assert "Marco Adarme" in message.html
        assert "Director Departamento de Sistemas" in message.html

    async def test_also_rings_the_bell_in_the_app(
        self, service, mock_notification_service
    ):
        with patch("api.services.improvement_plan_service.send_email"):
            await service.create(self._payload(), DIRECTOR)

        notification = mock_notification_service.create.await_args.args[0]

        assert notification.user_id == TEACHER["id"]
        # The teacher's own route: /planes/{id} is the director's screen.
        assert notification.link == "/mis-planes/7"

    async def test_a_dead_mail_server_does_not_lose_the_plan(self, service):
        """Test the plan is already created: SMTP failing cannot undo that."""

        with patch(
            "api.services.improvement_plan_service.send_email",
            side_effect=OSError("connection refused"),
        ):
            plan = await service.create(self._payload(), DIRECTOR)

        assert plan["id"] == 7

    async def test_a_failed_notification_does_not_lose_the_plan_either(
        self, service, mock_notification_service
    ):
        mock_notification_service.create.side_effect = RuntimeError("websocket down")

        with patch("api.services.improvement_plan_service.send_email"):
            plan = await service.create(self._payload(), DIRECTOR)

        assert plan["id"] == 7

    async def test_says_nothing_to_a_teacher_without_an_account(
        self, service, mock_repository, mock_notification_service
    ):
        """Test teachers imported from an evaluation may have no user yet."""

        mock_repository.get_teacher_contact.return_value = None

        with patch("api.services.improvement_plan_service.send_email") as send:
            plan = await service.create(self._payload(), DIRECTOR)

        assert plan["id"] == 7
        send.assert_not_called()
        mock_notification_service.create.assert_not_awaited()

    async def test_still_notifies_a_teacher_without_an_email(
        self, service, mock_repository, mock_notification_service
    ):
        """Test a missing address costs the mail, not the in-app notification."""

        mock_repository.get_teacher_contact.return_value = {
            "user_id": TEACHER["id"],
            "name": "Ada",
            "email": None,
        }

        with patch("api.services.improvement_plan_service.send_email") as send:
            await service.create(self._payload(), DIRECTOR)

        send.assert_not_called()
        mock_notification_service.create.assert_awaited_once()


class TestDelete:
    """Undoing a plan: the director's own call, and it takes everything."""

    async def test_deletes_and_audits(
        self, service, mock_repository, mock_audit_service
    ):
        with patch("api.services.improvement_plan_service.delete_plan_files"):
            assert await service.delete(7, DIRECTOR) is True

        mock_repository.delete.assert_awaited_once_with(7)
        mock_audit_service.log.assert_awaited_once()

    async def test_names_the_plan_in_the_audit_trail(
        self, service, mock_audit_service
    ):
        """Test the description is written while the row still exists."""

        with patch("api.services.improvement_plan_service.delete_plan_files"):
            await service.delete(7, DIRECTOR)

        description = mock_audit_service.log.await_args.kwargs["description"]

        assert "Plan de prueba" in description

    async def test_takes_the_files_off_the_disk_too(self, service):
        """Test the cascade is the database's; the PDFs are ours."""

        with patch(
            "api.services.improvement_plan_service.delete_plan_files"
        ) as delete_files:
            await service.delete(7, DIRECTOR)

        delete_files.assert_called_once_with(7)

    async def test_leaves_the_files_alone_when_the_row_was_already_gone(
        self, service, mock_repository
    ):
        mock_repository.delete.return_value = False

        with patch(
            "api.services.improvement_plan_service.delete_plan_files"
        ) as delete_files:
            assert await service.delete(7, DIRECTOR) is False

        delete_files.assert_not_called()

    async def test_a_director_of_another_department_may_not(self, service):
        with pytest.raises(PermissionDeniedError):
            await service.delete(7, OTHER_DIRECTOR)

    async def test_not_even_an_admin(self, service, mock_repository):
        """Test this belongs to whoever agreed the plan with the teacher."""

        with pytest.raises(PermissionDeniedError):
            await service.delete(7, ADMIN)

        mock_repository.delete.assert_not_awaited()

    async def test_the_teacher_may_not_delete_their_own_plan(self, service):
        with pytest.raises(PermissionDeniedError):
            await service.delete(7, TEACHER)

    async def test_raises_for_an_unknown_plan(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.delete(7, DIRECTOR)

    async def test_a_signed_agreement_does_not_block_it(
        self, service, mock_repository
    ):
        """Test a plan drawn up for the wrong teacher has to be undoable.

        Signing it does not make the mistake right; what protects a signed plan
        is the confirmation the director is shown, not a refusal here.
        """

        mock_repository.get_by_id.return_value = _plan(acta_status="FIRMADA")

        with patch("api.services.improvement_plan_service.delete_plan_files"):
            assert await service.delete(7, DIRECTOR) is True


class TestActaLock:
    """Once the acta is CERRADA its content freezes, but the plan lives on."""

    async def test_closing_requires_number_and_date(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(
            items=[{"commitment": "Llegar a tiempo"}]
        )

        with pytest.raises(ValidationError):
            await service.close_acta(7, ADMIN)

    async def test_closing_requires_a_commitment(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(
            acta_number="042", acta_date="2026-08-12", items=[{"commitment": None}]
        )

        with pytest.raises(ValidationError):
            await service.close_acta(7, ADMIN)

    async def test_closes_when_complete(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(
            acta_number="042",
            acta_date="2026-08-12",
            items=[{"commitment": "Llegar a tiempo"}],
        )

        result = await service.close_acta(7, ADMIN)

        assert result["acta_status"] == "CERRADA"
        mock_repository.set_acta_status.assert_awaited_once_with(
            7, "CERRADA", closed_by=ADMIN["id"]
        )

    async def test_cannot_close_twice(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(acta_status="CERRADA")

        with pytest.raises(ValidationError):
            await service.close_acta(7, ADMIN)

    async def test_locked_acta_rejects_content_edits(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(acta_status="CERRADA")

        with pytest.raises(ValidationError):
            await service.update(7, ImprovementPlanUpdate(acta_number="999"), ADMIN)

        mock_repository.update.assert_not_awaited()

    async def test_signed_acta_rejects_content_edits_too(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(acta_status="FIRMADA")

        with pytest.raises(ValidationError):
            await service.update(
                7,
                ImprovementPlanUpdate(items=[]),
                ADMIN,
            )

        mock_repository.update.assert_not_awaited()

    async def test_locked_acta_still_allows_editing_the_title(
        self, service, mock_repository
    ):
        mock_repository.get_by_id.return_value = _plan(acta_status="CERRADA")

        result = await service.update(
            7, ImprovementPlanUpdate(title="Nuevo título"), ADMIN
        )

        assert result["title"] == "Actualizado"
        mock_repository.update.assert_awaited_once()

    async def test_only_admin_may_reopen(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(acta_status="CERRADA")

        with pytest.raises(PermissionDeniedError):
            await service.reopen_acta(7, DIRECTOR)

    async def test_admin_reopens(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _plan(acta_status="CERRADA")
        mock_repository.set_acta_status.return_value = _plan(acta_status="BORRADOR")

        result = await service.reopen_acta(7, ADMIN)

        assert result["acta_status"] == "BORRADOR"
        mock_repository.set_acta_status.assert_awaited_once_with(7, "BORRADOR")


class TestGetAll:
    """Listing resolves the caller's department scope before delegating."""

    async def test_lists_with_the_resolved_department(self, service, mock_repository):
        from api.core.pagination import PaginationParams

        mock_repository.get_all = AsyncMock(return_value={"items": [], "total": 0})
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(DIRECTOR, pagination, teacher_id=55)

        assert result == {"items": [], "total": 0}
        mock_repository.get_all.assert_awaited_once_with(
            department_id=10,
            period_id=None,
            status=None,
            search=None,
            teacher_id=55,
            page=1,
            limit=10,
        )


class TestGetMyPlans:
    """A teacher's own plans, keyed off their linked teacher row."""

    async def test_returns_empty_without_a_linked_teacher(
        self, service, mock_repository
    ):
        mock_repository.get_teacher_by_user_id = MagicMock(return_value=None)

        result = await service.get_my_plans(TEACHER)

        assert result == []

    async def test_returns_the_teachers_plans(self, service, mock_repository):
        mock_repository.get_teacher_by_user_id = MagicMock(
            return_value=MagicMock(id=55)
        )
        mock_repository.get_by_teacher = AsyncMock(return_value=[_plan()])

        result = await service.get_my_plans(TEACHER)

        assert result == [_plan()]
        mock_repository.get_by_teacher.assert_awaited_once_with(55)


class TestGetCandidatesAndAtRisk:
    """Both require a resolved department and use the institutional threshold."""

    async def test_get_candidates_uses_the_resolved_department_and_threshold(
        self, service, mock_repository
    ):
        mock_repository.get_candidates = AsyncMock(return_value=[{"teacher_id": 1}])

        result = await service.get_candidates(DIRECTOR, 3)

        assert result == [{"teacher_id": 1}]
        mock_repository.get_candidates.assert_awaited_once_with(
            department_id=10, period_id=3, threshold=3.5
        )

    async def test_get_at_risk_uses_the_resolved_department_and_threshold(
        self, service, mock_repository
    ):
        mock_repository.get_at_risk = AsyncMock(return_value=[{"teacher_id": 1}])

        result = await service.get_at_risk(DIRECTOR, 3)

        assert result == [{"teacher_id": 1}]
        mock_repository.get_at_risk.assert_awaited_once_with(
            department_id=10, period_id=3, threshold=3.5
        )

    async def test_get_candidates_requires_a_department_for_admin(
        self, service, mock_repository
    ):
        with pytest.raises(ValidationError):
            await service.get_candidates(ADMIN, 3)


class TestGetEvaluatedPeriods:
    async def test_uses_the_resolved_department(self, service, mock_repository):
        mock_repository.get_evaluated_periods = AsyncMock(
            return_value=[{"id": 1}]
        )

        result = await service.get_evaluated_periods(DIRECTOR)

        assert result == [{"id": 1}]
        mock_repository.get_evaluated_periods.assert_awaited_once_with(10)


class TestGetTeacherCourses:
    """A director may only prefill forms for their own department's teachers."""

    async def test_admin_may_query_any_teacher(self, service, mock_repository):
        mock_repository.get_teacher_courses = AsyncMock(
            return_value=[{"course_code": "BD101"}]
        )

        result = await service.get_teacher_courses(55, 3, ADMIN)

        assert result == [{"course_code": "BD101"}]

    async def test_director_of_the_teachers_department_may_query(
        self, service, mock_repository
    ):
        mock_repository.get_teacher_department_id = MagicMock(return_value=10)
        mock_repository.get_teacher_courses = AsyncMock(return_value=[])

        await service.get_teacher_courses(55, 3, DIRECTOR)

        mock_repository.get_teacher_courses.assert_awaited_once_with(55, 3)

    async def test_director_of_another_department_is_forbidden(
        self, service, mock_repository
    ):
        mock_repository.get_teacher_department_id = MagicMock(return_value=99)

        with pytest.raises(PermissionDeniedError):
            await service.get_teacher_courses(55, 3, DIRECTOR)


class TestGetHistory:
    """Cross-period history is scoped the same way a single plan is."""

    async def test_raises_when_the_teacher_has_no_history(
        self, service, mock_repository
    ):
        mock_repository.get_history = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFoundError):
            await service.get_history(55, ADMIN)

    async def test_admin_may_see_any_teacher(self, service, mock_repository):
        mock_repository.get_history = AsyncMock(
            return_value={"department_id": 10, "plans": []}
        )

        result = await service.get_history(55, ADMIN)

        assert result["plans"] == []

    async def test_director_of_another_department_is_forbidden(
        self, service, mock_repository
    ):
        mock_repository.get_history = AsyncMock(
            return_value={"department_id": 99, "plans": []}
        )

        with pytest.raises(PermissionDeniedError):
            await service.get_history(55, DIRECTOR)


class TestUpsertCaseReport:
    async def test_updates_and_audits(
        self, service, mock_repository, mock_audit_service
    ):
        mock_repository.upsert_case_report = AsyncMock(
            return_value=_plan(complaint="Queja del programa")
        )

        result = await service.upsert_case_report(
            7, ImprovementPlanCaseReportUpsert(complaint="Queja del programa"), DIRECTOR
        )

        assert result["complaint"] == "Queja del programa"
        mock_repository.upsert_case_report.assert_awaited_once_with(
            7, ImprovementPlanCaseReportUpsert(complaint="Queja del programa"),
            reported_by=DIRECTOR["id"],
        )
        mock_audit_service.log.assert_awaited_once()

    async def test_a_teacher_cannot_report_a_case(self, service, mock_repository):
        with pytest.raises(PermissionDeniedError):
            await service.upsert_case_report(
                7, ImprovementPlanCaseReportUpsert(complaint="Queja"), TEACHER
            )


class TestUpdateCheckpoint:
    async def test_updates_and_audits(
        self, service, mock_repository, mock_audit_service
    ):
        mock_repository.update_checkpoint = AsyncMock(
            return_value=_plan(status="EN_SEGUIMIENTO")
        )

        result = await service.update_checkpoint(
            7, 3, ImprovementPlanCheckpointUpdate(notes="Avance"), DIRECTOR
        )

        assert result["status"] == "EN_SEGUIMIENTO"
        mock_audit_service.log.assert_awaited_once()

    async def test_raises_when_checkpoint_missing(self, service, mock_repository):
        mock_repository.update_checkpoint = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFoundError):
            await service.update_checkpoint(
                7, 999, ImprovementPlanCheckpointUpdate(notes="Avance"), DIRECTOR
            )

    async def test_a_teacher_cannot_fill_a_checkpoint(self, service, mock_repository):
        with pytest.raises(PermissionDeniedError):
            await service.update_checkpoint(
                7, 3, ImprovementPlanCheckpointUpdate(notes="Avance"), TEACHER
            )


class TestClosePlan:
    """Closing a plan records the verdict and best-effort announces it."""

    async def test_closes_and_audits(self, service, mock_repository, mock_audit_service):
        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="CUMPLIDO")
        )

        with patch("api.services.improvement_plan_service.send_email"):
            result = await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), DIRECTOR
            )

        assert result["result"] == "CUMPLIDO"
        mock_repository.close.assert_awaited_once_with(7, "CUMPLIDO", None)
        mock_audit_service.log.assert_awaited_once()

    async def test_a_teacher_cannot_close_their_own_plan(self, service, mock_repository):
        with pytest.raises(PermissionDeniedError):
            await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), TEACHER
            )

    async def test_emails_and_notifies_the_teacher_of_the_result(
        self, service, mock_repository, mock_notification_service
    ):
        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="NO_CUMPLIDO")
        )

        with patch(
            "api.services.improvement_plan_service.send_email"
        ) as send:
            await service.close(
                7,
                ImprovementPlanClose(
                    result=CloseResult.NO_CUMPLIDO, reason="No alcanzó la meta"
                ),
                DIRECTOR,
            )

        send.assert_called_once()
        mock_notification_service.create.assert_awaited_once()
        notification = mock_notification_service.create.await_args.args[0]
        assert notification.user_id == TEACHER["id"]

    async def test_a_dead_mail_server_does_not_lose_the_closing(
        self, service, mock_repository
    ):
        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="CUMPLIDO")
        )

        with patch(
            "api.services.improvement_plan_service.send_email",
            side_effect=OSError("connection refused"),
        ):
            result = await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), DIRECTOR
            )

        assert result["status"] == "CERRADO"

    async def test_says_nothing_when_the_teacher_has_no_account(
        self, service, mock_repository, mock_notification_service
    ):
        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="CUMPLIDO")
        )
        mock_repository.get_teacher_contact.return_value = None

        with patch("api.services.improvement_plan_service.send_email") as send:
            await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), DIRECTOR
            )

        send.assert_not_called()
        mock_notification_service.create.assert_not_awaited()

    async def test_says_nothing_when_the_notification_fails(
        self, service, mock_repository, mock_notification_service
    ):
        """Test a failed in-app notification doesn't stop the email either."""

        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="CUMPLIDO")
        )
        mock_notification_service.create.side_effect = RuntimeError("down")

        with patch(
            "api.services.improvement_plan_service.send_email"
        ) as send:
            result = await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), DIRECTOR
            )

        assert result["status"] == "CERRADO"
        send.assert_called_once()

    async def test_no_email_without_an_address(
        self, service, mock_repository, mock_notification_service
    ):
        mock_repository.close = AsyncMock(
            return_value=_plan(status="CERRADO", result="CUMPLIDO")
        )
        mock_repository.get_teacher_contact.return_value = {
            "user_id": TEACHER["id"],
            "name": "Ada",
            "email": None,
        }

        with patch("api.services.improvement_plan_service.send_email") as send:
            await service.close(
                7, ImprovementPlanClose(result=CloseResult.CUMPLIDO), DIRECTOR
            )

        send.assert_not_called()
        mock_notification_service.create.assert_awaited_once()
