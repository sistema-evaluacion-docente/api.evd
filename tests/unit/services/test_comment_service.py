"""
Tests for CommentService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.schemas.comment import CommentFilters
from api.services.comment_service import CommentService


class TestCommentService:
    """Test suite for CommentService."""

    @pytest.fixture
    def mock_comments_repo(self):
        """Mock CommentsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_academic_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self, mock_comments_repo, mock_academic_periods_repo, mock_audit_service
    ):
        """Create service instance with mocked dependencies."""

        return CommentService(
            mock_comments_repo,
            mock_academic_periods_repo,
            mock_audit_service,
        )

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_comments(
        self, service, mock_comments_repo
    ):
        """Test get_all returns paginated comments."""

        items = [{"id": 1}, {"id": 2}]
        mock_comments_repo.search.return_value = (items, 2)

        filters = CommentFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"] == items
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        mock_comments_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_comment(self, service, mock_comments_repo):
        """Test get_by_id returns comment dict."""

        mock_comments_repo.get_by_id_enriched.return_value = {
            "id": 1,
            "original_text": "Test comment",
        }

        result = await service.get_by_id(1)

        assert result == {"id": 1, "original_text": "Test comment"}
        mock_comments_repo.get_by_id_enriched.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, service, mock_comments_repo
    ):
        """Test get_by_id returns None when comment not found."""

        mock_comments_repo.get_by_id_enriched.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_department_and_period_returns_counts(
        self, service, mock_comments_repo, mock_academic_periods_repo
    ):
        """Test count_by_department_and_period returns counts."""

        mock_period = MagicMock()
        mock_period.code = "2024-1"
        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.get_previous_period_code.return_value = "2023-2"

        mock_prev_period = MagicMock()
        mock_prev_period.id = 2
        mock_academic_periods_repo.get_by_code.return_value = mock_prev_period

        mock_comments_repo.count_by_department_and_period.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await service.count_by_department_and_period(
            department_id=1,
            academic_period_id=1,
            risk_level=None,
            pedagogical_category_id=None,
            teacher_id=None,
        )

        assert result["current_count"] == 10
        assert result["previous_count"] == 8
        mock_comments_repo.count_by_department_and_period.assert_called_once_with(
            1, 1, 2, None, None, None
        )

    @pytest.mark.asyncio
    async def test_count_by_department_and_period_without_previous(
        self, service, mock_comments_repo, mock_academic_periods_repo
    ):
        """Test count_by_department_and_period when no previous period exists."""

        mock_period = MagicMock()
        mock_period.code = "2024-1"
        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.get_previous_period_code.return_value = None

        mock_comments_repo.count_by_department_and_period.return_value = {
            "current_count": 5,
            "previous_count": None,
        }

        result = await service.count_by_department_and_period(
            department_id=1,
            academic_period_id=1,
        )

        assert result["current_count"] == 5
        assert result["previous_count"] is None
        mock_comments_repo.count_by_department_and_period.assert_called_once_with(
            1, 1, None, None, None, None
        )
