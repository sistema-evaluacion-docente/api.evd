"""
Controller for admin dashboard summary.
"""

from fastapi import Depends

from api.repositories.admin_dashboard import (
    AdminDashboardRepository,
    get_admin_dashboard_repository,
)


class AdminDashboardController:
    def __init__(self, repository: AdminDashboardRepository):
        self.repository = repository

    async def get_dashboard(self) -> dict:
        counts = await self.repository.get_counts()
        recent_audits = await self.repository.get_recent_audits_with_users(limit=10)
        periods = await self.repository.get_periods()

        return {
            "counts": counts,
            "recent_audits": recent_audits,
            "periods": periods,
        }


def get_admin_dashboard_controller(
    repository: AdminDashboardRepository = Depends(get_admin_dashboard_repository),
):
    return AdminDashboardController(repository)
