"""Tests for AcademicPeriodsController layer."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.academic_periods import AcademicPeriodsController
from api.core.pagination import PaginationParams
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodFilters,
    AcademicPeriodUpdate,
)


class TestAcademicPeriodsController:
    """Test suite for AcademicPeriodsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock AcademicPeriodService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.create = AsyncMock()
        service.update = AsyncMock()
        service.activate = AsyncMock()
        service.close = AsyncMock()
        service.delete = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return AcademicPeriodsController(mock_service)

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_service(self, controller, mock_service):
        """Test get_all delegates to service."""

        mock_service.get_all.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = AcademicPeriodFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {
            "id": 1,
            "code": "2024-1",
            "name": "Primer semestre 2024",
        }

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99}
        data = AcademicPeriodCreate(
            code="2024-1",
            name="Primer semestre 2024",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
        )
        mock_service.create.return_value = {
            "id": 1,
            "code": "2024-1",
            "name": "Primer semestre 2024",
        }

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["code"] == "2024-1"

    @pytest.mark.asyncio
    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99}
        data = AcademicPeriodUpdate(name="Nuevo nombre")
        mock_service.update.return_value = {
            "id": 1,
            "code": "2024-1",
            "name": "Nuevo nombre",
        }

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["name"] == "Nuevo nombre"

    @pytest.mark.asyncio
    async def test_activate_delegates_to_service(self, controller, mock_service):
        """Test activate delegates to service."""

        current_user = {"id": 99}
        mock_service.activate.return_value = {
            "id": 1,
            "code": "2024-1",
            "active": True,
        }

        result = await controller.activate(1, current_user)

        mock_service.activate.assert_called_once_with(1, current_user)
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_close_delegates_to_service(self, controller, mock_service):
        """Test close delegates to service."""

        current_user = {"id": 99}
        mock_service.close.return_value = {
            "id": 1,
            "code": "2024-1",
            "active": False,
        }

        result = await controller.close(1, current_user)

        mock_service.close.assert_called_once_with(1, current_user)
        assert result["active"] is False

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1, "code": "2024-1"}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None
