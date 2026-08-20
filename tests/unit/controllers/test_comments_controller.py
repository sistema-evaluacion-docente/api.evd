"""
Tests for CommentsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.comments import CommentsController
from api.core.pagination import PaginationParams
from api.schemas.comment import CommentFilters, CommentUpdate


class TestCommentsController:
    """Test suite for CommentsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock CommentService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.count_by_department_and_period = AsyncMock()
        service.update_classification = AsyncMock()
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

        mock_service.get_all.assert_called_once_with(filters, pagination, None)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_all_forwards_department_id_when_given(
        self, controller, mock_service
    ):
        """Test get_all forwards a given department_id to the service."""

        mock_service.get_all.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0,
        }

        filters = CommentFilters()
        pagination = PaginationParams(page=1, limit=10)
        await controller.get_all(filters, pagination, department_id=3)

        mock_service.get_all.assert_called_once_with(filters, pagination, 3)

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

    @pytest.mark.asyncio
    async def test_update_classification_delegates_to_service(
        self, controller, mock_service
    ):
        """Test update_classification delegates to service."""

        mock_service.update_classification.return_value = {
            "id": 1,
            "risk_level_modified_by_director": True,
        }

        data = CommentUpdate(risk_level=2)
        current_user = {"id": 7, "department_id": 1}
        result = await controller.update_classification(1, data, current_user)

        mock_service.update_classification.assert_called_once_with(
            1, data, current_user
        )
        assert result["risk_level_modified_by_director"] is True
