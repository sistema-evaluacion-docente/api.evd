"""Tests for AcademicPeriodService layer."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.models.academic_period import AcademicPeriodModel
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodFilters,
    AcademicPeriodUpdate,
)
from api.services.academic_period_service import AcademicPeriodService


class TestAcademicPeriodService:
    """Test suite for AcademicPeriodService."""

    @pytest.fixture
    def mock_academic_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_evaluations_repo(self):
        """Mock EvaluationsRepository."""

        repo = MagicMock()
        return repo

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self, mock_academic_periods_repo, mock_evaluations_repo, mock_audit_service
    ):
        """Create service instance with mocked dependencies."""

        return AcademicPeriodService(
            mock_academic_periods_repo,
            mock_evaluations_repo,
            mock_audit_service,
        )

    @pytest.fixture
    def mock_period(self):
        """Mock AcademicPeriodModel instance."""

        period = MagicMock(spec=AcademicPeriodModel)
        period.id = 1
        period.code = "2024-1"
        period.name = "Primer semestre 2024"
        period.start_date = date(2024, 1, 15)
        period.end_date = date(2024, 6, 15)
        period.evaluation_end_date = date(2024, 6, 30)
        period.final_evaluation_date = date(2024, 7, 15)
        period.active = False
        period.created_at = "2024-01-01T00:00:00Z"
        period.updated_at = "2024-01-01T00:00:00Z"
        return period

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_periods(
        self, service, mock_academic_periods_repo, mock_period
    ):
        """Test get_all returns paginated academic periods."""

        mock_academic_periods_repo.search.return_value = ([mock_period], 1)

        filters = AcademicPeriodFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, service, mock_academic_periods_repo, mock_period
    ):
        """Test get_by_id returns period dict when found."""

        mock_academic_periods_repo.get.return_value = mock_period

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["code"] == "2024-1"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_academic_periods_repo):
        """Test get_by_id returns None when not found."""

        mock_academic_periods_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_period_success(
        self,
        service,
        mock_academic_periods_repo,
        mock_audit_service,
        mock_period,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_academic_periods_repo.get_by_code.return_value = None
        mock_academic_periods_repo.overlaps_with.return_value = False
        mock_academic_periods_repo.create_period.return_value = mock_period

        data = AcademicPeriodCreate(
            code="2024-1",
            name="Primer semestre 2024",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
        )

        result = await service.create(data, current_user)

        assert result is not None
        mock_academic_periods_repo.create_period.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_period_duplicate_code_raises(
        self, service, mock_academic_periods_repo, mock_period
    ):
        """Test create raises when code already exists."""

        mock_academic_periods_repo.get_by_code.return_value = mock_period

        data = AcademicPeriodCreate(
            code="2024-1",
            name="Primer semestre 2024",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
        )

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_create_period_overlapping_dates_raises(
        self, service, mock_academic_periods_repo
    ):
        """Test create raises when dates overlap with existing period."""

        mock_academic_periods_repo.get_by_code.return_value = None
        mock_academic_periods_repo.overlaps_with.return_value = True

        data = AcademicPeriodCreate(
            code="2024-2",
            name="Segundo semestre 2024",
            start_date=date(2024, 5, 1),
            end_date=date(2024, 10, 1),
        )

        with pytest.raises(ValidationError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_period_success(
        self,
        service,
        mock_academic_periods_repo,
        mock_audit_service,
        mock_period,
        current_user,
    ):
        """Test update succeeds when period exists."""

        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.overlaps_with.return_value = False
        mock_academic_periods_repo.update_period.return_value = mock_period

        data = AcademicPeriodUpdate(name="Nuevo nombre")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_academic_periods_repo.update_period.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_period_not_found(
        self, service, mock_academic_periods_repo, current_user
    ):
        """Test update returns None when period not found."""

        mock_academic_periods_repo.get.return_value = None

        data = AcademicPeriodUpdate(name="Nuevo nombre")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_period_overlapping_dates_raises(
        self, service, mock_academic_periods_repo, mock_period
    ):
        """Test update raises when new dates overlap with existing period."""

        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.overlaps_with.return_value = True

        data = AcademicPeriodUpdate(
            start_date=date(2024, 5, 1),
            end_date=date(2024, 10, 1),
        )

        with pytest.raises(ValidationError):
            await service.update(1, data, {"id": 99})

    @pytest.mark.asyncio
    async def test_activate_period_success(
        self,
        service,
        mock_academic_periods_repo,
        mock_audit_service,
        mock_period,
        current_user,
    ):
        """Test activate succeeds when no other period is active."""

        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.get_active.return_value = None
        mock_academic_periods_repo.activate_period.return_value = mock_period

        result = await service.activate(1, current_user)

        assert result is not None
        mock_academic_periods_repo.activate_period.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_period_not_found(
        self, service, mock_academic_periods_repo, current_user
    ):
        """Test activate returns None when period not found."""

        mock_academic_periods_repo.get.return_value = None

        result = await service.activate(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_close_period_success(
        self,
        service,
        mock_academic_periods_repo,
        mock_audit_service,
        mock_period,
        current_user,
    ):
        """Test close succeeds when period is active."""

        mock_period.active = True
        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.close_period.return_value = mock_period

        result = await service.close(1, current_user)

        assert result is not None
        mock_academic_periods_repo.close_period.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_period_not_found(
        self, service, mock_academic_periods_repo, current_user
    ):
        """Test close returns None when period not found."""

        mock_academic_periods_repo.get.return_value = None

        result = await service.close(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_period_success(
        self,
        service,
        mock_academic_periods_repo,
        mock_evaluations_repo,
        mock_audit_service,
        mock_period,
        current_user,
    ):
        """Test delete succeeds when no evaluations exist."""

        mock_academic_periods_repo.get.return_value = mock_period
        mock_evaluations_repo.has_evaluations_for_period = AsyncMock(return_value=False)
        mock_academic_periods_repo.delete_period.return_value = mock_period

        result = await service.delete(1, current_user)

        assert result is not None
        mock_academic_periods_repo.delete_period.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_period_not_found(
        self, service, mock_academic_periods_repo, current_user
    ):
        """Test delete returns None when period not found."""

        mock_academic_periods_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_period_with_evaluations_raises(
        self, service, mock_academic_periods_repo, mock_evaluations_repo, mock_period
    ):
        """Test delete raises when period has evaluations."""

        mock_academic_periods_repo.get.return_value = mock_period
        mock_evaluations_repo.has_evaluations_for_period = AsyncMock(return_value=True)

        with pytest.raises(ValidationError):
            await service.delete(1, {"id": 99})
