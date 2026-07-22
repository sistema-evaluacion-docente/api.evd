"""Evaluations controller — thin delegation to EvaluationService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.evaluations import get_evaluation_service
from api.schemas.evaluation import EvaluationFilters
from api.services.evaluation_service import EvaluationService


class EvaluationsController:
    """Controller for evaluation-related operations."""

    def __init__(self, service: EvaluationService):
        self.service = service

    async def get_all(
        self,
        filters: EvaluationFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all evaluations based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, evaluation_id: int):
        """Retrieve an evaluation by ID."""

        return await self.service.get_by_id(evaluation_id)

    async def get_by_period(self, period_id: int):
        """Retrieve an evaluation by academic period ID."""

        return await self.service.get_by_period(period_id)

    async def get_summary(self, evaluation_id: int):
        """Get aggregated statistics for an evaluation."""

        return await self.service.get_summary(evaluation_id)

    async def get_dimension_averages(self, evaluation_id: int):
        """Get dimension-level averages for an evaluation."""

        return await self.service.get_dimension_averages(evaluation_id)

    async def get_teacher_detail(self, evaluation_id: int, teacher_id: int):
        """Get per-course and per-dimension detail for a teacher in an evaluation."""

        return await self.service.get_teacher_detail(evaluation_id, teacher_id)

    async def get_teacher_comments(self, evaluation_id: int, teacher_id: int):
        """Get comments grouped by course for a teacher in an evaluation."""

        return await self.service.get_teacher_comments(evaluation_id, teacher_id)

    async def get_teachers_by_period(
        self,
        academic_period_id: int,
        pagination: PaginationParams,
        search: str | None = None,
    ):
        """Get all teachers with their average evaluation scores for a given academic period."""

        return await self.service.get_teachers_by_period(
            academic_period_id, pagination, search
        )

    async def prepare_upload(
        self,
        filename: str | None,
        file_bytes: bytes,
        current_user: dict,
    ):
        """Validate, parse, and persist an evaluation PDF upload."""

        return await self.service.prepare_upload(filename, file_bytes, current_user)

    async def trigger_analysis(self, evaluation_id: int):
        """Validate preconditions for triggering AI analysis."""

        return await self.service.trigger_analysis(evaluation_id)

    async def update_status(self, evaluation_id: int, active: bool, current_user: dict):
        """Activate or deactivate an evaluation."""

        return await self.service.update_status(evaluation_id, active, current_user)


def get_evaluations_controller(
    service: EvaluationService = Depends(get_evaluation_service),
):
    """Dependency injection for EvaluationsController."""

    return EvaluationsController(service)
