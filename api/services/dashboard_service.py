"""Service for teacher dashboard — combines multiple data sources into one response."""

from api.repositories.evaluations import EvaluationsRepository
from api.repositories.stats import StatsRepository


class DashboardService:
    """Service for teacher dashboard operations."""

    def __init__(
        self,
        evaluations_repository: EvaluationsRepository,
        stats_repository: StatsRepository,
    ):
        self.evaluations_repository = evaluations_repository
        self.stats_repository = stats_repository

    async def get_dashboard(self, teacher_id: int, evaluation_id: int) -> dict | None:
        """Get combined dashboard data for a teacher in a specific evaluation period."""

        evaluation_detail = self.evaluations_repository.get_teacher_detail(
            evaluation_id, teacher_id
        )
        if not evaluation_detail:
            return None

        evaluation = self.evaluations_repository.get_by_id(evaluation_id)
        if not evaluation or not evaluation.academic_period_id:
            return None

        period_id = evaluation.academic_period_id

        period_comparison = await self.stats_repository.get_teacher_vs_previous_period(
            teacher_id, period_id
        )

        comments = self.evaluations_repository.get_teacher_comments(
            evaluation_id, teacher_id
        )

        matrix = await self.stats_repository.get_teacher_matrix(
            teacher_id, evaluation_id
        )

        return {
            "evaluation_detail": evaluation_detail,
            "period_comparison": period_comparison,
            "comments": comments,
            "matrix": matrix,
        }
