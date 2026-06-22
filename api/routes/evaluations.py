"""
Routes for evaluation operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.evaluations import EvaluationsController, get_evaluations_controller
from api.middlewares.auth import require_roles
from api.schemas.evaluation import EvaluationDetailResponse, EvaluationListResponse
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get(
    "/",
    response_model=EvaluationListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_evaluations(
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Endpoint to list all evaluations."""

    evaluations = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Evaluations found",
        data=evaluations,
        path="/evaluations",
    )


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_evaluation_by_id(
    evaluation_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Endpoint to get an evaluation by ID."""

    evaluation = await controller.get_by_id(evaluation_id)

    if not evaluation:
        return ResponseSchema(
            status=404,
            message="Evaluation not found",
            path=f"/evaluations/{evaluation_id}",
        )

    return ResponseSchema(
        status=200,
        message="Evaluation found",
        data=evaluation,
        path=f"/evaluations/{evaluation_id}",
    )
