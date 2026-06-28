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


def get_stats_controller(
    repository: StatsRepository = Depends(get_stats_repository),
):
    """Get stats controller"""

    return StatsController(repository)
