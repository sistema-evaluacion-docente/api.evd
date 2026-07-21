"""
Tests for CommentsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.comments import CommentsController
from api.core.pagination import PaginationParams
from api.schemas.comment import CommentFilters


class TestCommentsController:
    """Test suite for CommentsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock CommentService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.count_by_department_and_period = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return CommentsController(mock_service)

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

        filters = CommentFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {
            "id": 1,
            "original_text": "Test comment",
        }

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_count_by_department_and_period_delegates_to_service(
        self, controller, mock_service
    ):
        """Test count_by_department_and_period delegates to service."""

        mock_service.count_by_department_and_period.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await controller.count_by_department_and_period(
            department_id=1,
            academic_period_id=1,
            risk_level=2,
            pedagogical_category_id=None,
            teacher_id=5,
        )

        mock_service.count_by_department_and_period.assert_called_once_with(
            1, 1, 2, None, 5
        )
        assert result["current_count"] == 10
        assert result["previous_count"] == 8
