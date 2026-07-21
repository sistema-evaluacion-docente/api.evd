"""Dependency injection for statistics-related operations."""

from fastapi import Depends

from api.repositories.stats import StatsRepository, get_stats_repository
from api.services.stats_service import StatsService


def get_stats_service(
    stats_repository: StatsRepository = Depends(get_stats_repository),
) -> StatsService:
    """Dependency injection for StatsService."""

    return StatsService(stats_repository)
