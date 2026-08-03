"""Dependency injection for dashboard-related operations."""

from fastapi import Depends

from api.repositories.evaluations import (
    EvaluationsRepository,
    get_evaluations_repository,
)
from api.repositories.stats import StatsRepository, get_stats_repository
from api.services.dashboard_service import DashboardService


def get_dashboard_service(
    evaluations_repository: EvaluationsRepository = Depends(get_evaluations_repository),
    stats_repository: StatsRepository = Depends(get_stats_repository),
) -> DashboardService:
    """Dependency injection for DashboardService."""

    return DashboardService(evaluations_repository, stats_repository)
