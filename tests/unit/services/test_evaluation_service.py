"""
Tests for EvaluationService layer.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from api.models.evaluation import EvaluationModel
from api.schemas.evaluation import EvaluationFilters, UploadedPdf
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
        self, service, mock_evaluations_repo, mock_users_repo, mock_directors_repo
    ):
        """Test get_all returns paginated evaluations."""

        items = [{"id": 1}, {"id": 2}]
        mock_evaluations_repo.search.return_value = (items, 2)

        mock_user = MagicMock()
        mock_user.id = 10
        mock_users_repo.get_by_email.return_value = mock_user

        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director

        filters = EvaluationFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all("admin@test.com", filters, pagination)

        assert result["items"] == items
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        mock_evaluations_repo.search.assert_called_once_with(filters, pagination)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_evaluation_with_dimension_averages(
        self, service, mock_evaluations_repo
    ):
        """Test get_by_id merges dimension averages into the evaluation dict."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}
        dimension_averages = [
            {
                "dimension": "Desarrollo del Conocimiento",
                "average": 4.5,
                "question_count": 6,
                "questions": [],
            }
        ]
        mock_evaluations_repo.get_dimension_averages.return_value = dimension_averages

        result = await service.get_by_id(1)

        assert result["id"] == 1
        assert result["dimension_averages"] == dimension_averages
        mock_evaluations_repo.get_by_id_as_dict.assert_called_once_with(1, None)
        mock_evaluations_repo.get_dimension_averages.assert_called_once_with(1, None)

    @pytest.mark.asyncio
    async def test_get_by_id_restricts_every_figure_to_the_requested_modality(
        self, service, mock_evaluations_repo
    ):
        """Test the average, dimensions and counts come from one kind of program.

        The repository does the narrowing, so what the service must get right
        is handing the same modality to every figure it asks for."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}
        mock_evaluations_repo.get_dimension_averages.return_value = []

        result = await service.get_by_id(1, "DISTANCIA")

        assert result["modality"] == "DISTANCIA"
        mock_evaluations_repo.get_by_id_as_dict.assert_called_once_with(1, "DISTANCIA")
        mock_evaluations_repo.get_dimension_averages.assert_called_once_with(
            1, "DISTANCIA"
        )

    @pytest.mark.asyncio
    async def test_get_by_id_normalizes_the_modality(
        self, service, mock_evaluations_repo
    ):
        """Test a lowercase modality reaches the repository in canonical form."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {"id": 1}
        mock_evaluations_repo.get_dimension_averages.return_value = []

        await service.get_by_id(1, "presencial")

        mock_evaluations_repo.get_by_id_as_dict.assert_called_once_with(1, "PRESENCIAL")

    @pytest.mark.asyncio
    async def test_get_by_id_rejects_an_unknown_modality(
        self, service, mock_evaluations_repo
    ):
        """Test a modality outside the catalog never reaches the repository."""

        with pytest.raises(ValidationError):
            await service.get_by_id(1, "VIRTUAL")

        mock_evaluations_repo.get_by_id_as_dict.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_compares_the_previous_period_within_the_modality(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test presencial is never compared against a distancia average."""

        mock_evaluations_repo.get_by_id_as_dict.side_effect = [
            {
                "id": 1,
                "academic_period_code": "2025-2",
                "department_id": 3,
                "overall_average": 4.0,
            },
            {"id": 7, "overall_average": 3.5},
        ]
        mock_evaluations_repo.get_dimension_averages.side_effect = [[], []]

        mock_academic_periods_repo.get_previous_period_code.return_value = "2025-1"
        prev_period = MagicMock(id=9, code="2025-1", name="2025-1")
        mock_academic_periods_repo.get_by_code.return_value = prev_period
        mock_evaluations_repo.get_by_period_and_department.return_value = {"id": 7}

        await service.get_by_id(1, "PRESENCIAL")

        assert (
            mock_evaluations_repo.get_by_id_as_dict.call_args_list[-1][0]
            == (7, "PRESENCIAL")
        )
        assert (
            mock_evaluations_repo.get_dimension_averages.call_args_list[-1][0]
            == (7, "PRESENCIAL")
        )

    @pytest.mark.asyncio
    async def test_get_by_id_includes_previous_period_comparison(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test get_by_id attaches a dimension/question growth comparison against
        the department's evaluation in the previous academic period."""

        current = {
            "id": 1,
            "academic_period_code": "2025-2",
            "department_id": 5,
            "overall_average": 4.0,
        }
        current_dims = [
            {
                "dimension": "Desarrollo del Conocimiento",
                "average": 4.0,
                "question_count": 1,
                "questions": [{"code": "Q1", "text": "text", "score": 4.0}],
            }
        ]
        prev_period = MagicMock(id=9, code="2025-1", name="2025-1")
        prev_evaluation_ref = {"id": 2}
        prev_evaluation_full = {"id": 2, "overall_average": 3.0}
        prev_dims = [
            {
                "dimension": "Desarrollo del Conocimiento",
                "average": 3.0,
                "question_count": 1,
                "questions": [{"code": "Q1", "text": "text", "score": 3.0}],
            }
        ]

        mock_evaluations_repo.get_by_id_as_dict.side_effect = [
            current,
            prev_evaluation_full,
        ]
        mock_evaluations_repo.get_dimension_averages.side_effect = [
            current_dims,
            prev_dims,
        ]
        mock_academic_periods_repo.get_previous_period_code.return_value = "2025-1"
        mock_academic_periods_repo.get_by_code.return_value = prev_period
        mock_evaluations_repo.get_by_period_and_department.return_value = (
            prev_evaluation_ref
        )

        result = await service.get_by_id(1)

        comparison = result["comparison"]
        assert comparison["previous_period_code"] == "2025-1"
        assert comparison["current_average"] == 4.0
        assert comparison["old_average"] == 3.0
        assert comparison["average_difference"] == 1.0
        assert comparison["dimensions"][0]["difference"] == 1.0
        assert comparison["dimensions"][0]["questions"][0]["difference"] == 1.0
        mock_evaluations_repo.get_by_period_and_department.assert_called_once_with(
            9, 5
        )

    @pytest.mark.asyncio
    async def test_get_by_id_comparison_is_none_without_previous_evaluation(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test get_by_id's comparison is None when there is no previous period
        evaluation for the department."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "academic_period_code": "2025-2",
            "department_id": 5,
        }
        mock_evaluations_repo.get_dimension_averages.return_value = []
        mock_academic_periods_repo.get_previous_period_code.return_value = "2025-1"
        mock_academic_periods_repo.get_by_code.return_value = MagicMock(id=9)
        mock_evaluations_repo.get_by_period_and_department.return_value = None

        result = await service.get_by_id(1)

        assert result["comparison"] is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test get_by_id returns None when evaluation not found."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = None

        result = await service.get_by_id(999)

        assert result is None
        mock_evaluations_repo.get_dimension_averages.assert_not_called()

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
    async def test_get_dimension_detail_returns_none_when_not_found(
        self, service, mock_evaluations_repo
    ):
        """Test get_dimension_detail returns None when evaluation not found."""

        mock_evaluations_repo.get_by_id.return_value = None

        result = await service.get_dimension_detail(999, {"uid": "director-uid"})

        assert result is None

    @pytest.mark.asyncio
    async def test_get_dimension_detail_raises_permission_denied_when_user_not_found(
        self, service, mock_evaluations_repo, mock_users_repo, mock_evaluation
    ):
        """Test get_dimension_detail raises PermissionDeniedError when uid not in DB."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_users_repo.get_by_uid.return_value = None

        with pytest.raises(PermissionDeniedError):
            await service.get_dimension_detail(1, {"uid": "unknown-uid"})

    @pytest.mark.asyncio
    async def test_get_dimension_detail_raises_permission_denied_when_not_director(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test get_dimension_detail raises PermissionDeniedError when user is not a director."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_directors_repo.get_by_user_id.return_value = None

        with pytest.raises(PermissionDeniedError, match="departamento asociado"):
            await service.get_dimension_detail(1, {"uid": "director-uid"})

    @pytest.mark.asyncio
    async def test_get_dimension_detail_raises_permission_denied_wrong_department(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test get_dimension_detail raises PermissionDeniedError for a director
        of a different department."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 999
        mock_directors_repo.get_by_user_id.return_value = mock_director

        with pytest.raises(PermissionDeniedError, match="departamento asociado"):
            await service.get_dimension_detail(1, {"uid": "director-uid"})

    @pytest.mark.asyncio
    async def test_get_dimension_detail_returns_detail_for_own_department_director(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test get_dimension_detail returns the repository detail when the
        director belongs to the evaluation's department."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director

        detail = {
            "evaluation_id": 1,
            "period_code": "2024-1",
            "period_name": "2024-1",
            "department_average": 4.1,
            "dimensions": [],
        }
        mock_evaluations_repo.get_dimension_detail.return_value = detail

        result = await service.get_dimension_detail(1, {"uid": "director-uid"})

        assert result == detail
        mock_evaluations_repo.get_dimension_detail.assert_called_once_with(
            1, None, None, None
        )

    @pytest.mark.asyncio
    async def test_get_dimension_detail_passes_teacher_and_course_filters(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test get_dimension_detail forwards teacher_id/course_id to the repository."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director
        mock_evaluations_repo.get_dimension_detail.return_value = {
            "evaluation_id": 1,
            "dimensions": [],
        }

        await service.get_dimension_detail(
            1, {"uid": "director-uid"}, teacher_id=7, course_id=3
        )

        mock_evaluations_repo.get_dimension_detail.assert_called_once_with(
            1, 7, 3, None
        )

    @pytest.mark.asyncio
    async def test_get_dimension_detail_scopes_the_breakdown_to_one_modality(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test the modality reaches the repository in canonical form."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director
        mock_evaluations_repo.get_dimension_detail.return_value = {
            "evaluation_id": 1,
            "dimensions": [],
        }

        await service.get_dimension_detail(
            1, {"uid": "director-uid"}, teacher_id=7, modality="distancia"
        )

        mock_evaluations_repo.get_dimension_detail.assert_called_once_with(
            1, 7, None, "DISTANCIA"
        )

    @pytest.mark.asyncio
    async def test_get_dimension_detail_rejects_an_unknown_modality(
        self,
        service,
        mock_evaluations_repo,
        mock_users_repo,
        mock_directors_repo,
        mock_evaluation,
    ):
        """Test a modality outside the catalog never reaches the repository."""

        mock_evaluations_repo.get_by_id.return_value = mock_evaluation
        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_director = MagicMock()
        mock_director.department_id = 1
        mock_directors_repo.get_by_user_id.return_value = mock_director

        with pytest.raises(ValidationError):
            await service.get_dimension_detail(
                1, {"uid": "director-uid"}, modality="VIRTUAL"
            )

        mock_evaluations_repo.get_dimension_detail.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_teacher_detail_returns_none_when_period_not_found(
        self, service, mock_academic_periods_repo
    ):
        """Test get_teacher_detail returns None when the period name doesn't exist."""

        mock_academic_periods_repo.get_by_name.return_value = None

        result = await service.get_teacher_detail("2099-1", 10)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_teacher_detail_without_compare_previous_omits_previous_period(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test get_teacher_detail doesn't fetch or attach previous_period by default."""

        period = MagicMock()
        period.id = 2
        period.code = "2024-1"
        mock_academic_periods_repo.get_by_name.return_value = period
        mock_evaluations_repo.get_by_period_id.return_value = {"id": 5}
        mock_evaluations_repo.get_teacher_detail.return_value = {
            "teacher_id": 10,
            "overall_average": 4.0,
        }

        result = await service.get_teacher_detail("2024-1", 10)

        assert "previous_period" not in result
        mock_evaluations_repo.get_teacher_detail.assert_called_once_with(5, 10)
        mock_academic_periods_repo.get_previous_period_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_teacher_detail_with_compare_previous_includes_previous_period(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test compare_previous=True attaches the detail from the prior semester."""

        period = MagicMock()
        period.id = 2
        period.code = "2024-2"
        prev_period = MagicMock()
        prev_period.id = 1
        prev_period.code = "2024-1"

        mock_academic_periods_repo.get_by_name.return_value = period
        mock_academic_periods_repo.get_previous_period_code.return_value = "2024-1"
        mock_academic_periods_repo.get_by_code.return_value = prev_period
        mock_evaluations_repo.get_by_period_id.side_effect = [
            {"id": 5},
            {"id": 4},
        ]

        current_detail = {"teacher_id": 10, "overall_average": 4.0}
        previous_detail = {"teacher_id": 10, "overall_average": 3.5}
        mock_evaluations_repo.get_teacher_detail.side_effect = [
            current_detail,
            previous_detail,
        ]

        result = await service.get_teacher_detail("2024-2", 10, compare_previous=True)

        assert result["previous_period"] == previous_detail
        mock_academic_periods_repo.get_previous_period_code.assert_called_once_with(
            "2024-2"
        )
        mock_academic_periods_repo.get_by_code.assert_called_once_with("2024-1")
        mock_evaluations_repo.get_teacher_detail.assert_any_call(5, 10)
        mock_evaluations_repo.get_teacher_detail.assert_any_call(4, 10)

    @pytest.mark.asyncio
    async def test_get_teacher_detail_with_compare_previous_no_prior_evaluation(
        self, service, mock_evaluations_repo, mock_academic_periods_repo
    ):
        """Test previous_period is None when the teacher has no evaluation that semester."""

        period = MagicMock()
        period.id = 2
        period.code = "2024-1"

        mock_academic_periods_repo.get_by_name.return_value = period
        mock_academic_periods_repo.get_previous_period_code.return_value = "2023-2"
        mock_academic_periods_repo.get_by_code.return_value = None
        mock_evaluations_repo.get_by_period_id.return_value = {"id": 5}
        mock_evaluations_repo.get_teacher_detail.return_value = {
            "teacher_id": 10,
            "overall_average": 4.0,
        }

        result = await service.get_teacher_detail("2024-1", 10, compare_previous=True)

        assert result["previous_period"] is None

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

    @staticmethod
    def _pdf(name="presencial.pdf"):
        """An upload that passes the file-level checks."""

        return UploadedPdf(name, b"%PDF-1.4 fake content")

    @staticmethod
    def _parsed(
        period_code="2024-1",
        department_code="CS",
        modality="PRESENCIAL",
        teachers=None,
    ):
        """The parsed content of a well formed evaluation PDF."""

        return {
            "period_code": period_code,
            "department_code": department_code,
            "department_name": "SISTEMAS",
            "modality": modality,
            "teachers": teachers if teachers is not None else [{"code": "001"}],
        }

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_non_pdf(self, service):
        """Test prepare_upload rejects files that are not named as PDFs."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload(
                [UploadedPdf("test.txt", b"content")], {"uid": "admin-uid"}
            )

        assert exc_info.value.status_code == 400
        assert "PDF" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_a_file_that_only_looks_like_a_pdf(
        self, service
    ):
        """Test prepare_upload rejects content that is not really a PDF."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload(
                [UploadedPdf("test.pdf", b"not a pdf at all")], {"uid": "admin-uid"}
            )

        assert exc_info.value.status_code == 400
        assert "PDF válido" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_empty_file(self, service):
        """Test prepare_upload rejects empty files."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload(
                [UploadedPdf("test.pdf", b"")], {"uid": "admin-uid"}
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_a_request_without_files(self, service):
        """Test prepare_upload rejects an upload with nothing attached."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload([], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_more_than_two_pdfs(self, service):
        """Test prepare_upload accepts at most one PDF per modality."""

        with pytest.raises(HTTPException) as exc_info:
            await service.prepare_upload(
                [self._pdf(), self._pdf("distancia.pdf"), self._pdf("otro.pdf")],
                {"uid": "admin-uid"},
            )

        assert exc_info.value.status_code == 400
        assert "hasta 2" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_unparseable_pdf(self, service):
        """Test prepare_upload rejects PDFs that cannot be parsed."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            side_effect=Exception("parse error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 400
        assert "parse error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_missing_period_code(self, service):
        """Test prepare_upload rejects PDFs without period code."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(period_code=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 422
        assert "periodo" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_missing_department_code(self, service):
        """Test prepare_upload rejects PDFs without department code."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(department_code=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 422
        assert "departamento" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_a_pdf_without_modality(self, service):
        """Test prepare_upload rejects a document whose title names no modality.

        That title is the only place the kind of program appears, so a document
        without it is not the report the university publishes."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(modality=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 422
        assert "presenciales o a distancia" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_no_teachers(self, service):
        """Test prepare_upload rejects PDFs without teacher data."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(teachers=[]),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_pdfs_of_different_periods(self, service):
        """Test both PDFs of an evaluation must describe the same period."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            side_effect=[
                self._parsed(period_code="2024-1"),
                self._parsed(period_code="2024-2", modality="DISTANCIA"),
            ],
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    [self._pdf(), self._pdf("distancia.pdf")], {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "periodos académicos distintos" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_pdfs_of_different_departments(self, service):
        """Test both PDFs of an evaluation must describe the same department."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            side_effect=[
                self._parsed(department_code="52"),
                self._parsed(department_code="60", modality="DISTANCIA"),
            ],
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    [self._pdf(), self._pdf("distancia.pdf")], {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "departamentos distintos" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_two_pdfs_of_the_same_modality(self, service):
        """Test the same document cannot be uploaded twice as both modalities."""

        with patch(
            "api.services.evaluation_service.parse_pdf",
            side_effect=[
                self._parsed(modality="PRESENCIAL"),
                self._parsed(modality="PRESENCIAL"),
            ],
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload(
                    [self._pdf(), self._pdf("otro.pdf")], {"uid": "admin-uid"}
                )

        assert exc_info.value.status_code == 422
        assert "misma modalidad" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prepare_upload_rejects_unknown_department(
        self, service, mock_academic_periods_repo, mock_evaluations_repo
    ):
        """Test prepare_upload rejects PDFs with unknown department."""

        mock_period = MagicMock()
        mock_period.id = 1
        mock_academic_periods_repo.get_by_code.return_value = mock_period
        mock_evaluations_repo.get_department_by_code.return_value = None

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(department_code="UNKNOWN"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

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
        mock_evaluations_repo.get_department_by_code.return_value = mock_department

        mock_evaluations_repo.get_by_period_and_department.return_value = {
            "id": 1,
            "active": True,
            "status": "COMPLETED",
        }

        with patch(
            "api.services.evaluation_service.parse_pdf",
            return_value=self._parsed(),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.prepare_upload([self._pdf()], {"uid": "admin-uid"})

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
        mock_evaluations_repo.get_department_by_code.return_value = mock_department

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
                    return_value=self._parsed(),
                ):
                    with patch(
                        "api.services.evaluation_service.evaluation_to_dict",
                        return_value={"id": 2},
                    ):
                        result, parsed = await service.prepare_upload(
                            [self._pdf()], {"uid": "admin-uid"}
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
        mock_evaluations_repo.get_department_by_code.return_value = mock_department

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
                    return_value=self._parsed(),
                ):
                    with patch(
                        "api.services.evaluation_service.evaluation_to_dict",
                        return_value={"id": 1},
                    ):
                        result, parsed = await service.prepare_upload(
                            [self._pdf()], {"uid": "admin-uid"}
                        )

        mock_academic_periods_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_upload_stores_both_pdfs_under_one_evaluation(
        self,
        service,
        mock_academic_periods_repo,
        mock_evaluations_repo,
        mock_users_repo,
    ):
        """Test the presencial and distancia documents end up in a single evaluation.

        Both files are written to disk under names that keep their modality,
        the two paths are stored comma-separated, and the teachers of both are
        merged into the parsed data handed to the background task."""

        mock_period = MagicMock()
        mock_period.id = 1
        mock_academic_periods_repo.get_by_code.return_value = mock_period

        mock_department = MagicMock()
        mock_department.id = 1
        mock_evaluations_repo.get_department_by_code.return_value = mock_department
        mock_evaluations_repo.get_by_period_and_department.return_value = None

        mock_user = MagicMock()
        mock_user.id = 10
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_evaluations_repo.create_evaluation.return_value = MagicMock(
            spec=EvaluationModel
        )

        presencial = self._parsed(teachers=[{"code": "001", "groups": [{"g": 1}]}])
        distancia = self._parsed(
            modality="DISTANCIA",
            teachers=[
                {"code": "001", "groups": [{"g": 2}]},
                {"code": "002", "groups": [{"g": 3}]},
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.services.evaluation_service.config") as mock_config:
                mock_config.UPLOAD_DIR = tmpdir
                with patch(
                    "api.services.evaluation_service.parse_pdf",
                    side_effect=[presencial, distancia],
                ):
                    with patch(
                        "api.services.evaluation_service.evaluation_to_dict",
                        return_value={"id": 3},
                    ):
                        _, parsed = await service.prepare_upload(
                            [self._pdf(), self._pdf("distancia.pdf")],
                            {"uid": "admin-uid"},
                        )

            stored = mock_evaluations_repo.create_evaluation.call_args.kwargs["pdf_url"]
            paths = stored.split(",")

            assert len(paths) == 2
            assert [os.path.basename(p).split("_")[0] for p in paths] == [
                "presencial",
                "distancia",
            ]
            assert all(os.path.isfile(path) for path in paths)

        assert [teacher["code"] for teacher in parsed["teachers"]] == ["001", "002"]
        assert parsed["teachers"][0]["groups"] == [{"g": 1}, {"g": 2}]

    @pytest.mark.asyncio
    async def test_get_pdf_path_raises_not_found_when_evaluation_missing(
        self, service, mock_evaluations_repo
    ):
        """Test get_pdf_path raises ResourceNotFoundError when evaluation doesn't exist."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.get_pdf_path(999, {"roles": ["ADMIN"]})

    @pytest.mark.asyncio
    async def test_get_pdf_path_allows_admin(self, service, mock_evaluations_repo):
        """Test get_pdf_path allows ADMIN regardless of department."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/file.pdf",
        }

        result = await service.get_pdf_path(
            1, {"roles": ["ADMIN"], "department_id": 999}
        )

        assert result == "uploads/evaluations/2024-1/CS/file.pdf"

    @pytest.mark.asyncio
    async def test_get_pdf_path_allows_director_of_same_department(
        self, service, mock_evaluations_repo
    ):
        """Test get_pdf_path allows a director whose department matches."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/file.pdf",
        }

        result = await service.get_pdf_path(
            1, {"roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 1}
        )

        assert result == "uploads/evaluations/2024-1/CS/file.pdf"

    @pytest.mark.asyncio
    async def test_get_pdf_path_denies_director_of_other_department(
        self, service, mock_evaluations_repo
    ):
        """Test get_pdf_path denies a director from a different department."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/file.pdf",
        }

        with pytest.raises(PermissionDeniedError):
            await service.get_pdf_path(
                1, {"roles": ["DIRECTOR DE DEPARTAMENTO"], "department_id": 2}
            )

    @pytest.mark.asyncio
    async def test_get_pdf_path_denies_docente(self, service, mock_evaluations_repo):
        """Test get_pdf_path denies a plain DOCENTE."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/file.pdf",
        }

        with pytest.raises(PermissionDeniedError):
            await service.get_pdf_path(1, {"roles": ["DOCENTE"], "department_id": 1})

    @pytest.mark.asyncio
    async def test_get_pdf_path_serves_the_first_pdf_by_default(
        self, service, mock_evaluations_repo
    ):
        """Test an evaluation with both documents serves one without asking."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": (
                "uploads/evaluations/2024-1/CS/presencial_a.pdf,"
                "uploads/evaluations/2024-1/CS/distancia_b.pdf"
            ),
        }

        result = await service.get_pdf_path(1, {"roles": ["ADMIN"]})

        assert result == "uploads/evaluations/2024-1/CS/presencial_a.pdf"

    @pytest.mark.asyncio
    async def test_get_pdf_path_serves_the_requested_modality(
        self, service, mock_evaluations_repo
    ):
        """Test each kind of program can be downloaded on its own."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": (
                "uploads/evaluations/2024-1/CS/presencial_a.pdf,"
                "uploads/evaluations/2024-1/CS/distancia_b.pdf"
            ),
        }

        result = await service.get_pdf_path(1, {"roles": ["ADMIN"]}, "DISTANCIA")

        assert result == "uploads/evaluations/2024-1/CS/distancia_b.pdf"

    @pytest.mark.asyncio
    async def test_get_pdf_path_raises_not_found_for_a_missing_modality(
        self, service, mock_evaluations_repo
    ):
        """Test asking for a document the evaluation does not have is a 404."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/presencial_a.pdf",
        }

        with pytest.raises(ResourceNotFoundError):
            await service.get_pdf_path(1, {"roles": ["ADMIN"]}, "DISTANCIA")

    @pytest.mark.asyncio
    async def test_get_pdf_path_rejects_an_unknown_modality(
        self, service, mock_evaluations_repo
    ):
        """Test a modality outside the catalog is rejected."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": "uploads/evaluations/2024-1/CS/presencial_a.pdf",
        }

        with pytest.raises(ValidationError):
            await service.get_pdf_path(1, {"roles": ["ADMIN"]}, "VIRTUAL")

    @pytest.mark.asyncio
    async def test_get_pdf_path_raises_not_found_when_no_pdf(
        self, service, mock_evaluations_repo
    ):
        """Test get_pdf_path raises ResourceNotFoundError when evaluation has no PDF."""

        mock_evaluations_repo.get_by_id_as_dict.return_value = {
            "id": 1,
            "department_id": 1,
            "pdf_url": None,
        }

        with pytest.raises(ResourceNotFoundError):
            await service.get_pdf_path(1, {"roles": ["ADMIN"], "department_id": 1})

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
