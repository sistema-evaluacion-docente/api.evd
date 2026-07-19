"""
Tests for AuditsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.audits import AuditsController
from api.core.pagination import PaginationParams
from api.schemas.audit import AuditFilters


class TestAuditsController:
    """Test suite for AuditsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.list_audits = AsyncMock()
        service.get_by_id = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return AuditsController(mock_service)

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_service(self, controller, mock_service):
        """Test get_all delegates to service."""

        mock_service.list_audits.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.list_audits.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_all_with_filters_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_all with filters delegates to service."""

        mock_service.list_audits.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = AuditFilters(actor_id=99, entity_name="users", operation="CREATE")
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.list_audits.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_all_with_pagination_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_all with pagination delegates to service."""

        mock_service.list_audits.return_value = {
            "items": [],
            "total": 0,
            "page": 2,
            "limit": 20,
            "pages": 0,
        }

        filters = AuditFilters()
        pagination = PaginationParams(page=2, limit=20)
        result = await controller.get_all(filters, pagination)

        mock_service.list_audits.assert_called_once_with(filters, pagination)
        assert result["page"] == 2
        assert result["limit"] == 20

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_response(self, controller, mock_service):
        """Test get_all returns paginated response with items."""

        mock_service.list_audits.return_value = {
            "items": [
                {
                    "id": 1,
                    "user_id": 99,
                    "table_name": "users",
                    "operation": "CREATE",
                }
            ],
            "total": 1,
            "page": 1,
            "limit": 10,
            "pages": 1,
        }

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {
            "id": 1,
            "user_id": 99,
            "table_name": "users",
            "operation": "CREATE",
            "element_data": {"id": 1, "email": "test@example.com"},
        }

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1
        assert result["element_data"] is not None

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, controller, mock_service):
        """Test get_by_id returns None when not found."""

        mock_service.get_by_id.return_value = None

        result = await controller.get_by_id(999)

        mock_service.get_by_id.assert_called_once_with(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_element_data(self, controller, mock_service):
        """Test get_by_id returns audit with element_data."""

        mock_service.get_by_id.return_value = {
            "id": 1,
            "user_id": 99,
            "table_name": "users",
            "operation": "CREATE",
            "element": "User 1",
            "description": "Test",
            "element_data": {"id": 1, "email": "test@example.com"},
        }

        result = await controller.get_by_id(1)

        assert result["element_data"] is not None
        assert result["element_data"]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_all_empty_result(self, controller, mock_service):
        """Test get_all returns empty list when no audits found."""

        mock_service.list_audits.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0
