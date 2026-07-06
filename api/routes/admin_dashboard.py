"""
Routes for admin dashboard operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.admin_dashboard import (
    AdminDashboardController,
    get_admin_dashboard_controller,
)
from api.middlewares.auth import require_roles
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


@router.get(
    "/",
    responses={403: {"description": "Forbidden"}},
)
async def get_admin_dashboard(
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AdminDashboardController = Depends(get_admin_dashboard_controller),
):
    """Endpoint to get admin dashboard summary: counts, recent audits, and periods."""

    data = await controller.get_dashboard()

    return ResponseSchema(
        status=200,
        message="Admin dashboard data retrieved successfully",
        data=data,
        path="/admin/dashboard",
    )
