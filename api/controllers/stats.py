"""
Stats controller
"""

from fastapi.param_functions import Depends

from api.repositories.stats import StatsRepository, get_stats_repository


class StatsController:
    """Stats controller"""

    def __init__(self, repository: StatsRepository):
        self.repository = repository

    async def get_department_averages_by_period(
        self, department_id: int | None = None
    ) -> list[dict]:
        """Get global average per department per academic period."""

        return await self.repository.get_department_averages_by_period(department_id)

    async def get_department_average_with_previous(
        self, department_id: int, academic_period_id: int
    ) -> dict | None:
        """Get department average for a period with previous period comparison."""

        return await self.repository.get_department_average_with_previous(
            department_id, academic_period_id
        )

    async def get_teacher_performance_ranking(
        self, academic_period_id: int | None = None
    ) -> dict:
        """Get top 5 and bottom 5 teachers by overall average score."""

        return await self.repository.get_teacher_performance_ranking(academic_period_id)

    async def get_grade_distribution(
        self,
        academic_period_id: int | None = None,
        department_id: int | None = None,
        bin_size: float = 0.5,
    ) -> dict:
        """Get grade distribution histogram for teachers."""

        return await self.repository.get_grade_distribution(
            academic_period_id, department_id, bin_size
        )


def get_stats_controller(
    repository: StatsRepository = Depends(get_stats_repository),
):
    """Get stats controller"""

    return StatsController(repository)
