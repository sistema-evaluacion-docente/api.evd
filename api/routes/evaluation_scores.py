"""
Routes for evaluation score operations.
"""

from fastapi import Depends, Query

from api.controllers.evaluation_scores import (
    EvaluationScoresController,
    get_evaluation_scores_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.evaluation_score import (
    EvaluationScoreDetailResponse,
    EvaluationScoreListResponse,
)
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/evaluation-scores", tags=["Evaluation Scores"])


@router.get(
    "/",
    response_model=EvaluationScoreListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_evaluation_scores(
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationScoresController = Depends(get_evaluation_scores_controller),
):
    """Endpoint to list all evaluation scores."""

    scores = await controller.get_all()

    return ResponseSchema(
        status=200,
        message="Evaluation scores found",
        data=scores,
        path="/evaluation-scores",
    )


@router.get(
    "/{score_id}",
    response_model=EvaluationScoreDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_evaluation_score_by_id(
    score_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationScoresController = Depends(get_evaluation_scores_controller),
):
    """Endpoint to get an evaluation score by ID."""

    score = await controller.get_by_id(score_id)

    if not score:
        return ResponseSchema(
            status=404,
            message="Evaluation score not found",
            path=f"/evaluation-scores/{score_id}",
        )

    return ResponseSchema(
        status=200,
        message="Evaluation score found",
        data=score,
        path=f"/evaluation-scores/{score_id}",
    )


@router.get(
    "/by-evaluation/{evaluation_id}",
    response_model=EvaluationScoreListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_scores_by_evaluation(
    evaluation_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by group name"),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationScoresController = Depends(get_evaluation_scores_controller),
):
    """Endpoint to list all scores for a given evaluation with pagination and search."""

    result = await controller.get_by_evaluation_paginated(
        evaluation_id,
        page=page,
        limit=limit,
        search=search,
    )

    return ResponseSchema(
        status=200,
        message="Evaluation scores found",
        data=result["scores"],
        pagination=Pagination(
            total=result["total"],
            page=page,
            limit=limit,
            pages=result["pages"],
        ),
        path=f"/evaluation-scores/by-evaluation/{evaluation_id}",
    )
