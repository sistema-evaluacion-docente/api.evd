"""
Tests for ProgramsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.programs import ProgramsController
from api.core.pagination import PaginationParams
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate


class TestProgramsController:
    """Test suite for ProgramsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock ProgramService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.create = AsyncMock()
        service.update = AsyncMock()
        service.delete = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return ProgramsController(mock_service)

    async def test_get_all_delegates_to_service(self, controller, mock_service):
        """Test get_all delegates to service."""

        mock_service.get_all.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = ProgramFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {
            "id": 1,
            "code": "IS",
            "name": "Ingeniería de Sistemas",
        }

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    async def test_create_delegates_to_service(self, controller, mock_service):
        """Test create delegates to service."""

        current_user = {"id": 99}
        data = ProgramCreate(name="Ingeniería de Sistemas", code="IS")
        mock_service.create.return_value = {
            "id": 1,
            "code": "IS",
            "name": "Ingeniería de Sistemas",
        }

        result = await controller.create(data, current_user)

        mock_service.create.assert_called_once_with(data, current_user)
        assert result["code"] == "IS"

    async def test_update_delegates_to_service(self, controller, mock_service):
        """Test update delegates to service."""

        current_user = {"id": 99}
        data = ProgramUpdate(name="Ingeniería Industrial")
        mock_service.update.return_value = {"id": 1, "name": "Ingeniería Industrial"}

        result = await controller.update(1, data, current_user)

        mock_service.update.assert_called_once_with(1, data, current_user)
        assert result["name"] == "Ingeniería Industrial"

    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"id": 99}
        mock_service.delete.return_value = {"id": 1}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result is not None
