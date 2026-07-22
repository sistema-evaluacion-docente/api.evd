"""
Tests for AuditsRepository layer.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.audit import AuditModel
from api.repositories.audits import AuditsRepository
from api.repositories.base import BaseRepository
from api.schemas.audit import AuditFilters


class TestAuditsRepository:
    """Test suite for AuditsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return AuditsRepository(mock_db)

    @pytest.fixture
    def mock_audit_model(self):
        """Mock AuditModel instance."""

        audit = MagicMock(spec=AuditModel)
        audit.id = 1
        audit.user_id = 99
        audit.table_name = "users"
        audit.operation = "CREATE"
        audit.element = "User 1"
        audit.description = "Creación del usuario test@example.com"
        audit.created_at = datetime(2024, 1, 1, 0, 0, 0)
        audit.updated_at = datetime(2024, 1, 1, 0, 0, 0)
        audit.user = None
        return audit

    def test_inherits_base_repository(self, repo):
        """Test AuditsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_search_no_filters(self, repo, mock_db, mock_audit_model):
        """Test search with no filters returns all audits."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert len(audits) == 1
        assert audits[0] == mock_audit_model
        mock_db.query.assert_called_once_with(AuditModel)

    def test_search_with_actor_id_filter(self, repo, mock_db, mock_audit_model):
        """Test search filters by actor_id."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters(actor_id=99)
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called

    def test_search_with_entity_name_filter(self, repo, mock_db, mock_audit_model):
        """Test search filters by entity_name."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters(entity_name="users")
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called

    def test_search_with_operation_filter(self, repo, mock_db, mock_audit_model):
        """Test search filters by operation."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters(operation="CREATE")
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called

    def test_search_with_date_range_filters(self, repo, mock_db, mock_audit_model):
        """Test search filters by date range."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 12, 31)
        filters = AuditFilters(date_from=date_from, date_to=date_to)
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called

    def test_search_with_search_filter(self, repo, mock_db, mock_audit_model):
        """Test search filters by search term in element and description."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters(search="test")
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called

    def test_search_empty_result(self, repo, mock_db):
        """Test search returns empty list when no audits found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value.limit.return_value.all.return_value = []

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 0
        assert len(audits) == 0

    def test_get_by_id_with_element_data_found(self, repo, mock_db, mock_audit_model):
        """Test get_by_id_with_element_data returns audit when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_audit_model

        result = repo.get_by_id_with_element_data(1)

        assert result is not None
        assert result["id"] == 1
        assert result["table_name"] == "users"
        mock_db.query.assert_called_once_with(AuditModel)

    def test_get_by_id_with_element_data_not_found(self, repo, mock_db):
        """Test get_by_id_with_element_data returns None when not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_id_with_element_data(999)

        assert result is None

    def test_create_audit(self, repo, mock_db):
        """Test create_audit creates a new audit log."""

        audit_data = {
            "user_id": 99,
            "table_name": "users",
            "operation": "CREATE",
            "element": "User 1",
            "description": "Test",
        }

        mock_audit = MagicMock(spec=AuditModel)
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        result = repo.create_audit(audit_data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_search_orders_by_created_at_desc(self, repo, mock_db, mock_audit_model):
        """Test search orders results by created_at descending."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters()
        pagination = PaginationParams(page=1, limit=10)

        repo.search(filters, pagination)

        mock_query.order_by.assert_called_once()

    def test_search_with_multiple_filters(self, repo, mock_db, mock_audit_model):
        """Test search applies multiple filters together."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_audit_model
        ]

        filters = AuditFilters(
            actor_id=99, entity_name="users", operation="CREATE", search="test"
        )
        pagination = PaginationParams(page=1, limit=10)

        audits, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.called
