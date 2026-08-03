"""Service for teacher dashboard — combines multiple data sources into one response."""

from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.evaluations import EvaluationsRepository
from api.repositories.stats import StatsRepository


class DashboardService:
    """Service for teacher dashboard operations."""

    def __init__(
        self,
        evaluations_repository: EvaluationsRepository,
        stats_repository: StatsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
    ):
        self.evaluations_repository = evaluations_repository
        self.stats_repository = stats_repository
        self.academic_periods_repository = academic_periods_repository

    async def get_dashboard(
        self, teacher_id: int, period_name: str, department_id: int
    ) -> dict | None:
        """Get combined dashboard data for a teacher in a specific academic period."""

        period = self.academic_periods_repository.get_by_name(period_name)
        if not period:
            return None

        evaluation_data = self.evaluations_repository.get_by_period_and_department(
            period.id, department_id
        )
        if not evaluation_data:
            return None

        evaluation_id = evaluation_data["id"]

        evaluation_detail = self.evaluations_repository.get_teacher_detail(
            evaluation_id, teacher_id
        )
        if not evaluation_detail:
            return None

        period_comparison = await self.stats_repository.get_teacher_vs_previous_period(
            teacher_id, period.id
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
