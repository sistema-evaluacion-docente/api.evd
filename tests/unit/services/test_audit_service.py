"""Tests for AuditService layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.audit import AuditModel
from api.schemas.audit import AuditFilters
from api.services.audit_service import AuditService


class TestAuditService:
    """Test suite for AuditService."""

    @pytest.fixture
    def mock_audits_repo(self):
        """Mock AuditsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        repo.search.return_value = ([], 0)
        repo.create_audit.return_value = MagicMock(spec=AuditModel)
        return repo

    @pytest.fixture
    def service(self, mock_audits_repo):
        """Create service instance with mocked dependencies."""

        return AuditService(mock_audits_repo)

    @pytest.fixture
    def mock_audit(self):
        """Mock AuditModel instance."""

        audit = MagicMock(spec=AuditModel)
        audit.id = 1
        audit.user_id = 99
        audit.table_name = "users"
        audit.operation = "CREATE"
        audit.element = "User 1"
        audit.description = "Creación del usuario test@example.com"
        audit.created_at = "2024-01-01T00:00:00Z"
        audit.updated_at = "2024-01-01T00:00:00Z"
        audit.user = None
        return audit

    @pytest.mark.asyncio
    async def test_list_audits_returns_paginated_audits(
        self, service, mock_audits_repo, mock_audit
    ):
        """Test list_audits returns paginated audits."""

        mock_audits_repo.search.return_value = ([mock_audit], 1)

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.list_audits(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1
        mock_audits_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_list_audits_with_filters(
        self, service, mock_audits_repo, mock_audit
    ):
        """Test list_audits passes filters to repository."""

        mock_audits_repo.search.return_value = ([mock_audit], 1)

        filters = AuditFilters(actor_id=99, entity_name="users", operation="CREATE")
        pagination = PaginationParams(page=1, limit=10)

        result = await service.list_audits(filters, pagination)

        mock_audits_repo.search.assert_called_once_with(filters, pagination)
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_audits_empty_result(self, service, mock_audits_repo):
        """Test list_audits returns empty list when no audits found."""

        mock_audits_repo.search.return_value = ([], 0)

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.list_audits(filters, pagination)

        assert result["total"] == 0
        assert result["items"] == []
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_returns_audit_with_element_data(
        self, service, mock_audits_repo
    ):
        """Test get_by_id returns audit with element_data."""

        expected = {
            "id": 1,
            "user_id": 99,
            "user": None,
            "table_name": "users",
            "operation": "CREATE",
            "element": "User 1",
            "description": "Test",
            "element_data": {"id": 1, "email": "test@example.com"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_audits_repo.get_by_id_with_element_data.return_value = expected

        result = await service.get_by_id(1)

        assert result == expected
        mock_audits_repo.get_by_id_with_element_data.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, service, mock_audits_repo
    ):
        """Test get_by_id returns None when audit not found."""

        mock_audits_repo.get_by_id_with_element_data.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_log_creates_audit_record(self, service, mock_audits_repo):
        """Test log creates an audit record with correct data."""

        await service.log(
            action="CREATE",
            entity_name="users",
            entity_id=1,
            actor_id=99,
            description="Creación del usuario test@example.com",
        )

        mock_audits_repo.create_audit.assert_called_once_with(
            {
                "user_id": 99,
                "table_name": "users",
                "operation": "CREATE",
                "element": "users 1",
                "description": "Creación del usuario test@example.com",
            }
        )
        mock_audits_repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_none_actor_id(self, service, mock_audits_repo):
        """Test log handles None actor_id."""

        await service.log(
            action="CREATE",
            entity_name="users",
            entity_id=1,
            actor_id=None,
            description="Test",
        )

        mock_audits_repo.create_audit.assert_called_once_with(
            {
                "user_id": None,
                "table_name": "users",
                "operation": "CREATE",
                "element": "users 1",
                "description": "Test",
            }
        )

    @pytest.mark.asyncio
    async def test_log_with_none_description(self, service, mock_audits_repo):
        """Test log handles None description."""

        await service.log(
            action="DELETE",
            entity_name="teachers",
            entity_id=5,
            actor_id=99,
            description=None,
        )

        mock_audits_repo.create_audit.assert_called_once_with(
            {
                "user_id": 99,
                "table_name": "teachers",
                "operation": "DELETE",
                "element": "teachers 5",
                "description": None,
            }
        )

    @pytest.mark.asyncio
    async def test_log_with_string_entity_id(self, service, mock_audits_repo):
        """Test log handles string entity_id."""

        await service.log(
            action="UPDATE",
            entity_name="settings",
            entity_id="app_name",
            actor_id=99,
            description="Test",
        )

        mock_audits_repo.create_audit.assert_called_once_with(
            {
                "user_id": 99,
                "table_name": "settings",
                "operation": "UPDATE",
                "element": "settings app_name",
                "description": "Test",
            }
        )
