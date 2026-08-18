"""
Unit tests for ImprovementPlanService.

Focus on the business rules the official UFPS forms impose: who may see or touch
a plan, the duplicate-plan guard, and the acta lock.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.exceptions import (
    PermissionDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.schemas.improvement_plan import (
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
def service(mock_repository, mock_settings_repository, mock_audit_service):
    return ImprovementPlanService(
        mock_repository, mock_settings_repository, mock_audit_service
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
