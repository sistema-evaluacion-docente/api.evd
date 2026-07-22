"""
Routes for evaluation question score operations.
"""

from fastapi import Depends

from api.controllers.evaluation_question_scores import (
    EvaluationQuestionScoresController,
    get_evaluation_question_scores_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.evaluation_question_score import (
    EvaluationQuestionScoreDetailResponse,
    EvaluationQuestionScoreListResponse,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/evaluation-question-scores", tags=["Evaluation Question Scores"])


@router.get(
    "/{question_score_id}",
    response_model=EvaluationQuestionScoreDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_evaluation_question_score_by_id(
    question_score_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationQuestionScoresController = Depends(
        get_evaluation_question_scores_controller
    ),
):
    """Endpoint to get an evaluation question score by ID."""

    question_score = await controller.get_by_id(question_score_id)

    if not question_score:
        return ResponseSchema(
            status=404,
            message="Evaluation question score not found",
            path=f"/evaluation-question-scores/{question_score_id}",
        )

    return ResponseSchema(
        status=200,
        message="Evaluation question score found",
        data=question_score,
        path=f"/evaluation-question-scores/{question_score_id}",
    )


@router.get(
    "/by-evaluation-score/{evaluation_score_id}",
    response_model=EvaluationQuestionScoreListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_question_scores_by_evaluation_score(
    evaluation_score_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationQuestionScoresController = Depends(
        get_evaluation_question_scores_controller
    ),
):
    """Endpoint to list all question scores for a given evaluation score."""

    question_scores = await controller.get_by_evaluation_score(evaluation_score_id)

    return ResponseSchema(
        status=200,
        message="Evaluation question scores found",
        data=question_scores,
        path=f"/evaluation-question-scores/by-evaluation-score/{evaluation_score_id}",
    )
