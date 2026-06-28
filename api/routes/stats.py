"""
Routes for statistics operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.controllers.stats import StatsController, get_stats_controller
from api.middlewares.auth import require_roles
from api.schemas.response import ResponseSchema
from api.schemas.stats import StatsListResponse
from api.schemas.user import RoleName

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/",
    response_model=StatsListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_department_averages_by_period(
    department_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get global department averages by academic period."""

    stats = await controller.get_department_averages_by_period(department_id)

    return ResponseSchema(
        status=200,
        message="Department averages by period found",
        data=stats,
        path="/stats",
    )
