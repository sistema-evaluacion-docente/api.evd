"""
Tests for EvaluationsController layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluations import EvaluationsController
from api.core.pagination import PaginationParams
from api.schemas.evaluation import EvaluationFilters


class TestEvaluationsController:
    """Test suite for EvaluationsController."""

    @pytest.fixture
    def mock_service(self):
        """Mock EvaluationService."""

        service = MagicMock()
        service.get_all = AsyncMock()
        service.get_by_id = AsyncMock()
        service.get_by_period = AsyncMock()
        service.get_summary = AsyncMock()
        service.get_dimension_averages = AsyncMock()
        service.get_teacher_detail = AsyncMock()
        service.get_teacher_comments = AsyncMock()
        service.get_teachers_by_period = AsyncMock()
        service.prepare_upload = AsyncMock()
        service.trigger_analysis = AsyncMock()
        service.update_status = AsyncMock()
        service.delete = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_service):
        """Create controller instance with mocked service."""

        return EvaluationsController(mock_service)

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

        filters = EvaluationFilters()
        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_all(filters, pagination)

        mock_service.get_all.assert_called_once_with(filters, pagination)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_service(self, controller, mock_service):
        """Test get_by_id delegates to service."""

        mock_service.get_by_id.return_value = {"id": 1, "status": "COMPLETED"}

        result = await controller.get_by_id(1)

        mock_service.get_by_id.assert_called_once_with(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_period_delegates_to_service(self, controller, mock_service):
        """Test get_by_period delegates to service."""

        mock_service.get_by_period.return_value = {"id": 1, "academic_period_id": 5}

        result = await controller.get_by_period(5)

        mock_service.get_by_period.assert_called_once_with(5)
        assert result["academic_period_id"] == 5

    @pytest.mark.asyncio
    async def test_get_summary_delegates_to_service(self, controller, mock_service):
        """Test get_summary delegates to service."""

        mock_service.get_summary.return_value = {
            "evaluation_id": 1,
            "department_average": 4.5,
        }

        result = await controller.get_summary(1)

        mock_service.get_summary.assert_called_once_with(1)
        assert result["department_average"] == 4.5

    @pytest.mark.asyncio
    async def test_get_dimension_averages_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_dimension_averages delegates to service."""

        mock_service.get_dimension_averages.return_value = [
            {"dimension": "A", "average": 4.0}
        ]

        result = await controller.get_dimension_averages(1)

        mock_service.get_dimension_averages.assert_called_once_with(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_teacher_detail_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_teacher_detail delegates to service."""

        mock_service.get_teacher_detail.return_value = {
            "teacher_id": 10,
            "overall_average": 4.5,
        }

        result = await controller.get_teacher_detail(1, 10)

        mock_service.get_teacher_detail.assert_called_once_with(1, 10)
        assert result["teacher_id"] == 10

    @pytest.mark.asyncio
    async def test_get_teacher_comments_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_teacher_comments delegates to service."""

        mock_service.get_teacher_comments.return_value = {
            "teacher_id": 10,
            "courses": [],
        }

        result = await controller.get_teacher_comments(1, 10)

        mock_service.get_teacher_comments.assert_called_once_with(1, 10)
        assert result["teacher_id"] == 10

    @pytest.mark.asyncio
    async def test_get_teachers_by_period_delegates_to_service(
        self, controller, mock_service
    ):
        """Test get_teachers_by_period delegates to service."""

        mock_service.get_teachers_by_period.return_value = {
            "teacher_count": 5,
            "teachers": [],
        }

        pagination = PaginationParams(page=1, limit=10)
        result = await controller.get_teachers_by_period(1, pagination, None)

        mock_service.get_teachers_by_period.assert_called_once_with(1, pagination, None)
        assert result["teacher_count"] == 5

    @pytest.mark.asyncio
    async def test_prepare_upload_delegates_to_service(self, controller, mock_service):
        """Test prepare_upload delegates to service."""

        mock_service.prepare_upload.return_value = (
            {"id": 1, "status": "PROCESSING"},
            {"period_code": "2024-1"},
        )

        current_user = {"uid": "admin-uid"}
        result = await controller.prepare_upload("test.pdf", b"pdf bytes", current_user)

        mock_service.prepare_upload.assert_called_once_with(
            "test.pdf", b"pdf bytes", current_user
        )
        assert result[0]["status"] == "PROCESSING"

    @pytest.mark.asyncio
    async def test_trigger_analysis_delegates_to_service(
        self, controller, mock_service
    ):
        """Test trigger_analysis delegates to service."""

        mock_service.trigger_analysis.return_value = {
            "id": 1,
            "status": "COMPLETED",
            "ai_status": "PENDING",
        }

        result = await controller.trigger_analysis(1)

        mock_service.trigger_analysis.assert_called_once_with(1)
        assert result["ai_status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_update_status_delegates_to_service(self, controller, mock_service):
        """Test update_status delegates to service."""

        current_user = {"uid": "director-uid"}
        mock_service.update_status.return_value = {"id": 1, "active": False}

        result = await controller.update_status(1, False, current_user)

        mock_service.update_status.assert_called_once_with(1, False, current_user)
        assert result["active"] is False

    @pytest.mark.asyncio
    async def test_delete_delegates_to_service(self, controller, mock_service):
        """Test delete delegates to service."""

        current_user = {"uid": "director-uid"}
        mock_service.delete.return_value = {"id": 1, "department_id": 1}

        result = await controller.delete(1, current_user)

        mock_service.delete.assert_called_once_with(1, current_user)
        assert result["id"] == 1
