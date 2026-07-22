"""
Tests for EvaluationService layer.
"""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from api.models.evaluation import EvaluationModel
from api.schemas.evaluation import EvaluationFilters
from api.services.evaluation_service import EvaluationService


class TestEvaluationService:
    """Test suite for EvaluationService."""

    @pytest.fixture
    def mock_evaluations_repo(self):
        """Mock EvaluationsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_academic_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_directors_repo(self):
        """Mock DirectorsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_evaluations_repo,
        mock_users_repo,
        mock_academic_periods_repo,
        mock_directors_repo,
        mock_audit_service,
    ):
        """Create service instance with mocked dependencies."""

        return EvaluationService(
            mock_evaluations_repo,
            mock_users_repo,
            mock_academic_periods_repo,
            mock_directors_repo,
            mock_audit_service,
        )

    @pytest.fixture
    def mock_evaluation(self):
        """Mock EvaluationModel instance."""

        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.user_id = 10
        evaluation.academic_period_id = 1
        evaluation.department_id = 1
        evaluation.pdf_url = "/tmp/test.pdf"
        evaluation.active = True
        evaluation.status = "COMPLETED"
        evaluation.ai_status = "PENDING"
        evaluation.count = 5
        evaluation.created_at = "2024-01-01T00:00:00Z"
        evaluation.updated_at = "2024-01-01T00:00:00Z"
        evaluation.academic_period = MagicMock()
        evaluation.academic_period.name = "2024-1"
        evaluation.academic_period.code = "2024-1"
        return evaluation

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "uid": "admin-uid", "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_evaluations(
        self, service, mock_evaluations_repo
    ):
        """Test get_all returns paginated evaluations."""

        items = [{"id": 1}, {"id": 2}]
        mock_evaluations_repo.search.return_value = (items, 2)

        filters = EvaluationFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"] == items
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        mock_evaluations_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_evaluation(self, service, mock_evaluations_repo):
        """Test get_by_id returns evaluation dict."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}

        result = await service.get_by_id(1)

        assert result == {"id": 1}
        mock_evaluations_repo.get_by_id_as_dict.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test get_by_id returns None when evaluation not found."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_period_returns_evaluation(
        self, service, mock_evaluations_repo
    ):
        """Test get_by_period returns evaluation dict."""

        mock_evaluations_repo.get_by_period_id.return_value = {"id": 1}

        result = await service.get_by_period(1)

        assert result == {"id": 1}
        mock_evaluations_repo.get_by_period_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_summary_returns_statistics(self, service, mock_evaluations_repo):
        """Test get_summary returns aggregated statistics."""

        summary = {
            "evaluation_id": 1,
            "department_average": 4.5,
            "ranking": [],
        }
        mock_evaluations_repo.get_summary.return_value = summary

        result = await service.get_summary(1)

        assert result == summary
        mock_evaluations_repo.get_summary.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_dimension_averages_returns_list(
        self, service, mock_evaluations_repo
    ):
        """Test get_dimension_averages returns dimension averages."""

        averages = [{"dimension": "A", "average": 4.0}]
        mock_evaluations_repo.get_dimension_averages.return_value = averages

        result = await service.get_dimension_averages(1)

        assert result == averages
        mock_evaluations_repo.get_dimension_averages.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_trigger_analysis_raises_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test trigger_analysis raises ResourceNotFoundError when evaluation not found."""

        mock_evaluations_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.trigger_analysis(999)

    @pytest.mark.asyncio
    async def test_trigger_analysis_raises_when_not_completed(
        self, service, mock_evaluations_repo, mock_evaluation
    ):
        """Test trigger_analysis raises ValidationError when status is not COMPLETED."""

        mock_evaluation.status = "PROCESSING"
        mock_evaluations_repo.get_by_id.return_value = mock_evaluation

        with pytest.raises(ValidationError, match="procesada completamente"):
            await service.trigger_analysis(1)

    @pytest.mark.asyncio
    async def test_trigger_analysis_raises_when_already_analyzing(
        self, service, mock_evaluations_repo, mock_evaluation
    ):
        """Test trigger_analysis raises ValidationError when ai_status is ANALYZING."""

        mock_evaluation.ai_status = "ANALYZING"
        mock_evaluations_repo.get_by_id.return_value = mock_evaluation

        with pytest.raises(ValidationError, match="análisis de IA ya está en progreso"):
            await service.trigger_analysis(1)

    @pytest.mark.asyncio
    async def test_trigger_analysis_returns_evaluation_when_valid(
        self, service, mock_evaluations_repo, mock_evaluation
    ):
        """Test trigger_analysis returns evaluation dict when preconditions are met."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_evaluations_repo.db = MagicMock()

        with patch(
            "api.services.evaluation_service.evaluation_to_dict",
            return_value={"id": 1, "status": "COMPLETED"},
        ):
            result = await service.trigger_analysis(1)

        assert result["id"] == 1
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_update_status_activates_evaluation(
        self, service, mock_evaluations_repo, mock_users_repo, mock_audit_service
    ):
        """Test update_status activates evaluation and logs audit."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}
        mock_evaluations_repo.update_active_status.return_value = {
            "id": 1,
            "active": True,
        }
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user

        result = await service.update_status(1, True, {"uid": "admin-uid"})

        assert result["active"] is True
        mock_evaluations_repo.update_active_status.assert_called_once_with(1, True)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_deactivates_evaluation(
        self, service, mock_evaluations_repo, mock_users_repo
    ):
        """Test update_status deactivates evaluation and logs audit."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}
        mock_evaluations_repo.update_active_status.return_value = {
            "id": 1,
            "active": False,
        }
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user

        result = await service.update_status(1, False, {"uid": "admin-uid"})

        assert result["active"] is False
        mock_evaluations_repo.update_active_status.assert_called_once_with(1, False)

    @pytest.mark.asyncio
    async def test_update_status_returns_none_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test update_status returns None when evaluation not found."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = None

        result = await service.update_status(999, True, {"uid": "admin-uid"})

        assert result is None

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_non_pdf(self, service):
        """Test prepare_upload rejects non-PDF files."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload("test.txt", b"content", {"uid": "admin-uid"})

        assert exc_info.value.status_code == 400
        assert "PDF" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_empty_file(self, service):
        """Test prepare_upload rejects empty files."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload("test.pdf", b"", {"uid": "admin-uid"})

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_unparseable_pdf(self, service):
        """Test prepare_upload rejects PDFs that cannot be parsed."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            side_effect=Exception("parse error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 400
        assert "parse error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_missing_period_code(self, service):
        """Test prepare_upload rejects PDFs without period code."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value={
                "period_code": None,
                "department_code": "CS",
                "teachers": [{}],
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "period" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_missing_department_code(self, service):
        """Test prepare_upload rejects PDFs without department code."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value={
                "period_code": "2024-1",
                "department_code": None,
                "teachers": [{}],
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "departamento" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_no_teachers(self, service):
        """Test prepare_upload rejects PDFs without teacher data."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value={
                "period_code": "2024-1",
                "department_code": "CS",
                "teachers": [],
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_unknown_department(
        self, service, mock_academic_periods_repo, mock_evaluations_repo
    ):
        """Test prepare_upload rejects PDFs with unknown department."""

        mock_period = MagicMock()
        mock_period.id = 1
        mock_academic_periods_repo.get_by_code.return_value = mock_period
        mock_evaluations_repo.db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value={
                "period_code": "2024-1",
                "department_code": "UNKNOWN",
                "teachers": [{}],
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "UNKNOWN" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_duplicate_completed_evaluation(
        self, service, mock_academic_periods_repo, mock_evaluations_repo
    ):
        """Test prepare_upload rejects duplicate evaluation when one is COMPLETED and active."""

        mock_period = MagicMock()
        mock_period.id = 1
        mock_academic_periods_repo.get_by_code.return_value = mock_period

        mock_department = MagicMock()
        mock_department.id = 1
        mock_evaluations_repo.db.query.return_value.filter.return_value.first.return_value = (
            mock_department
        )

        mock_evaluations_repo.get_by_period_and_department.return_value = {
            "id": 1,
            "active": True,
            "status": "COMPLETED",
        }

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value={
                "period_code": "2024-1",
                "department_code": "CS",
                "teachers": [{}],
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_prepare_upload_deletes_failed_evaluation_before_creating_new(
        self,
        service,
        mock_academic_periods_repo,
        mock_evaluations_repo,
        mock_users_repo,
    ):
        """Test prepare_upload deletes existing FAILED evaluation before creating new one."""

        mock_period = MagicMock()
        mock_period.id = 1
        mock_academic_periods_repo.get_by_code.return_value = mock_period

        mock_department = MagicMock()
        mock_department.id = 1
        mock_evaluations_repo.db.query.return_value.filter.return_value.first.return_value = (
            mock_department
        )

        mock_evaluations_repo.get_by_period_and_department.return_value = {
            "id": 99,
            "active": False,
            "status": "FAILED",
        }

        mock_user = MagicMock()
        mock_user.id = 10
        mock_users_repo.get_by_uid.return_value = mock_user

        mock_new_eval = MagicMock(spec=EvaluationModel)
        mock_evaluations_repo.create_evaluation.return_value = mock_new_eval

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.services.evaluation_service.config") as mock_config:
                mock_config.UPLOAD_DIR = tmpdir
                with patch(
                    "api.services.evaluation_service.parse_pdf",
                    return_value={
                        "period_code": "2024-1",
                        "department_code": "CS",
                        "teachers": [{}],
                    },
                ):
                    with patch(
                        "api.services.evaluation_service.evaluation_to_dict",
                        return_value={"id": 2},
                    ):
                        result, parsed = await service.prepare_upload(
                            "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                        )

        mock_evaluations_repo.delete_evaluation.assert_called_once_with(99)
        assert result["id"] == 2

    @pytest.mark.asyncio
    async def test_prepare_upload_creates_period_if_not_exists(
        self,
        service,
        mock_academic_periods_repo,
        mock_evaluations_repo,
        mock_users_repo,
    ):
        """Test prepare_upload creates academic period if it doesn't exist."""

        mock_academic_periods_repo.get_by_code.return_value = None

        mock_new_period = MagicMock()
        mock_new_period.id = 1
        mock_academic_periods_repo.create.return_value = mock_new_period

        mock_department = MagicMock()
        mock_department.id = 1
        mock_evaluations_repo.db.query.return_value.filter.return_value.first.return_value = (
            mock_department
        )

        mock_evaluations_repo.get_by_period_and_department.return_value = None

        mock_user = MagicMock()
        mock_user.id = 10
        mock_users_repo.get_by_uid.return_value = mock_user

        mock_new_eval = MagicMock(spec=EvaluationModel)
        mock_evaluations_repo.create_evaluation.return_value = mock_new_eval

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.services.evaluation_service.config") as mock_config:
                mock_config.UPLOAD_DIR = tmpdir
                with patch(
                    "api.services.evaluation_service.parse_pdf",
                    return_value={
                        "period_code": "2024-1",
                        "department_code": "CS",
                        "teachers": [{}],
                    },
                ):
                    with patch(
                        "api.services.evaluation_service.evaluation_to_dict",
                        return_value={"id": 1},
                    ):
                        result, parsed = await service.prepare_upload(
                            "test.pdf", b"fake pdf", {"uid": "admin-uid"}
                        )

        mock_academic_periods_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_teachers_by_period_returns_paginated_result(
        self, service, mock_evaluations_repo
    ):
        """Test get_teachers_by_period returns paginated teachers."""

        mock_evaluations_repo.get_teachers_by_period.return_value = {
            "period_id": 1,
            "period_code": "2024-1",
            "period_name": "2024-1",
            "teacher_count": 2,
            "teachers": [{"teacher_id": 1}, {"teacher_id": 2}],
        }

        pagination = PaginationParams(page=1, limit=10)
        result = await service.get_teachers_by_period(1, pagination, None)

        assert result["teacher_count"] == 2
        assert len(result["teachers"]) == 2
        assert result["page"] == 1
        assert result["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_teachers_by_period_returns_none_when_period_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test get_teachers_by_period returns None when period not found."""

        mock_evaluations_repo.get_teachers_by_period.return_value = None

        pagination = PaginationParams(page=1, limit=10)
        result = await service.get_teachers_by_period(999, pagination, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_returns_none_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test delete returns None when evaluation not found."""

        mock_evaluations_repo.get_by_id.return_value = None

        result = await service.delete(999, {"uid": "director-uid"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_raises_permission_denied_when_user_not_found(
        self, service, mock_evaluations_repo, mock_users_repo, mock_evaluation
    ):
        """Test delete raises PermissionDeniedError when current_user uid not in DB."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_users_repo.get_by_uid.return_value = None

        with pytest.raises(PermissionDeniedError):
            await service.delete(1, {"uid": "unknown-uid"})

    @pytest.mark.asyncio
    async def test_delete_raises_permission_denied_when_not_director(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test delete raises PermissionDeniedError when user is not a director."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_directors_repo.get_by_user_id.return_value = None

        with pytest.raises(PermissionDeniedError, match="departamento asociado"):
            await service.delete(1, {"uid": "director-uid"})

    @pytest.mark.asyncio
    async def test_delete_raises_permission_denied_wrong_department(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test delete raises PermissionDeniedError when director belongs to different department."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 999
        mock_directors_repo.get_by_user_id.return_value = mock_director

        with pytest.raises(PermissionDeniedError, match="departamento asociado"):
            await service.delete(1, {"uid": "director-uid"})

    @pytest.mark.asyncio
    async def test_delete_deletes_evaluation_and_logs_audit(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_audit_service,
        mock_evaluation,
    ):
        """Test delete succeeds when user is the director of the evaluation's department."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director

        with patch(
            "api.services.evaluation_service.evaluation_to_dict",
            return_value={
                "id": 1,
                "department_id": 1,
                "academic_period_code": "2024-1",
            },
        ):
            result = await service.delete(1, {"uid": "director-uid"})

        assert result["id"] == 1
        mock_evaluations_repo.delete_evaluation.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once_with(
            action="DELETE",
            entity_name="evaluations",
            entity_id=1,
            actor_id=99,
            description="Se eliminó la evaluación 1 del período 2024-1",
        )
