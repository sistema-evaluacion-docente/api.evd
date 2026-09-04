"""Tests for AdminDashboardRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.models.audit import AuditModel
from api.repositories.admin_dashboard import AdminDashboardRepository


class TestAdminDashboardRepository:
    """Test suite for AdminDashboardRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return AdminDashboardRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_counts_returns_all_entity_counts(self, repo, mock_db):
        """Test get_counts queries every counted entity and defaults to 0."""

        query = mock_db.query.return_value
        query.scalar.return_value = None
        query.filter.return_value.scalar.return_value = None

        result = await repo.get_counts()

        assert result == {
            "departments": 0,
            "faculties": 0,
            "users": 0,
            "active_users": 0,
            "teachers": 0,
            "evaluations": 0,
            "academic_periods": 0,
            "active_periods": 0,
        }

    @pytest.mark.asyncio
    async def test_get_counts_returns_nonzero_scalars(self, repo, mock_db):
        """Test get_counts passes through non-null scalar counts."""

        query = mock_db.query.return_value
        query.scalar.return_value = 5
        query.filter.return_value.scalar.return_value = 3

        result = await repo.get_counts()

        assert result["departments"] == 5
        assert result["active_users"] == 3

    @pytest.mark.asyncio
    async def test_get_recent_audits_serializes_each_row(self, repo, mock_db):
        """Test get_recent_audits maps rows through the audit serializer."""

        audit = MagicMock(spec=AuditModel)
        audit.id = 1
        audit.user_id = None
        audit.user = None
        audit.table_name = "users"
        audit.operation = "CREATE"
        audit.element = "1"
        audit.description = "desc"
        audit.created_at = None
        audit.updated_at = None
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            audit
        ]

        result = await repo.get_recent_audits(limit=5)

        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_recent_audits_with_users_attaches_user_info(
        self, repo, mock_db
    ):
        """Test get_recent_audits_with_users enriches audits with actor info."""

        audit = MagicMock(spec=AuditModel)
        audit.id = 1
        audit.user_id = 2
        audit.user = None
        audit.table_name = "users"
        audit.operation = "CREATE"
        audit.element = "1"
        audit.description = "desc"
        audit.created_at = None
        audit.updated_at = None

        user = MagicMock()
        user.id = 2
        user.name = "Ana"
        user.avatar_url = "url"

        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            audit
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = [user]

        result = await repo.get_recent_audits_with_users(limit=5)

        assert result[0]["user_name"] == "Ana"
        assert result[0]["user_avatar"] == "url"

    @pytest.mark.asyncio
    async def test_get_recent_audits_with_users_skips_lookup_without_user_ids(
        self, repo, mock_db
    ):
        """Test the user lookup is skipped when no audit has a user_id."""

        audit = MagicMock(spec=AuditModel)
        audit.id = 1
        audit.user_id = None
        audit.user = None
        audit.table_name = "users"
        audit.operation = "CREATE"
        audit.element = "1"
        audit.description = "desc"
        audit.created_at = None
        audit.updated_at = None
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            audit
        ]

        result = await repo.get_recent_audits_with_users(limit=5)

        assert "user_name" not in result[0]

    @pytest.mark.asyncio
    async def test_get_periods_serializes_each_row(self, repo, mock_db):
        """Test get_periods returns dicts with stringified dates."""

        period = MagicMock()
        period.id = 1
        period.code = "2026-1"
        period.name = "2026-1"
        period.start_date = None
        period.end_date = None
        period.active = None
        mock_db.query.return_value.order_by.return_value.all.return_value = [period]

        result = await repo.get_periods()

        assert result == [
            {
                "id": 1,
                "code": "2026-1",
                "name": "2026-1",
                "start_date": None,
                "end_date": None,
                "active": False,
            }
        ]
