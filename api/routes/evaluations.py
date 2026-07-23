"""
Routes for evaluation operations.
"""

from fastapi import (
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from api.controllers.evaluations import (
    EvaluationsController,
    get_evaluations_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.database import get_db
from api.middlewares.auth import require_roles, get_current_user
from api.models.evaluation import EvaluationModel as EvaluationORM
from api.repositories.stats import StatsRepository, get_stats_repository
from api.schemas.evaluation import (
    EvaluationFiltersDep,
    EvaluationOut,
    EvaluationStatusUpdate,
)
from api.schemas.evaluation_summary import (
    DimensionAverageItem,
    EvaluationSummaryOut,
    QuestionItem,
    TeacherCommentsOut,
    TeacherEvaluationDetail,
    TeacherPeriodEvaluation,
)
from api.schemas.user import RoleName
from api.utils.dimensions import QUESTIONS
from api.utils.evaluation_processor import (
    analyze_evaluation_comments,
    process_evaluation,
)
from api.utils.evaluation_excel_export import (
    build_evaluation_report,
    evaluation_streaming_response,
)
from api.utils.teacher_excel_export import (
    build_teacher_report,
    teacher_streaming_response,
)

router = EnvelopeRouter(prefix="/evaluations", tags=["Evaluations"])

_EVAL_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.post(
    "/upload",
    status_code=202,
    response_model=EvaluationOut,
)
async def upload_evaluation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Upload a teacher evaluation PDF for a department."""

    pdf_bytes = await file.read()

    evaluation, parsed = await controller.prepare_upload(
        filename=file.filename,
        file_bytes=pdf_bytes,
        current_user=current_user,
    )

    background_tasks.add_task(process_evaluation, evaluation["id"], parsed)

    return evaluation


@router.get(
    "/questions",
    response_model=list[QuestionItem],
)
async def get_question_catalog(
    _=Depends(require_roles(_EVAL_ROLES)),
):
    """Return the full catalog of evaluation questions with their code, text, and dimension."""

    return QUESTIONS


@router.get(
    "/",
    response_model=list[EvaluationOut],
    responses={403: {"description": "Forbidden"}},
)
async def get_all_evaluations(
    filters: EvaluationFiltersDep,
    pagination: PaginationDep,
    current_user=Depends(get_current_user),
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Endpoint to list all evaluations with optional filters."""

    return await controller.get_all(current_user.email, filters, pagination)


@router.get(
    "/by-period/{period_id}",
    response_model=EvaluationOut,
)
async def get_evaluation_by_period(
    period_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Endpoint to get an evaluation by academic period ID."""

    evaluation = await controller.get_by_period(period_id)

    if not evaluation:
        raise HTTPException(
            status_code=404, detail="Evaluación no encontrada para este periodo"
        )

    return evaluation


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationOut,
)
async def get_evaluation_by_id(
    evaluation_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Endpoint to get an evaluation by ID."""

    evaluation = await controller.get_by_id(evaluation_id)

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    return evaluation


@router.get(
    "/period/{period_id}/teachers",
    response_model=list[TeacherPeriodEvaluation],
)
async def get_teachers_by_period(
    period_id: int,
    pagination: PaginationDep,
    search: str | None = None,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return all teachers with their average evaluation scores for a given academic period."""

    result = await controller.get_teachers_by_period(period_id, pagination, search)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Periodo academico no encontrado o no existen evaluaciones para este periodo",
        )

    return {
        "total": result["teacher_count"],
        "page": result["page"],
        "limit": result["limit"],
        "pages": result["pages"],
        "items": result["teachers"],
    }


@router.get(
    "/{evaluation_id}/summary",
    response_model=EvaluationSummaryOut,
)
async def get_evaluation_summary(
    evaluation_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return aggregated department statistics for an evaluation."""

    summary = await controller.get_summary(evaluation_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    return summary


@router.get(
    "/{evaluation_id}/dimension-averages",
    response_model=list[DimensionAverageItem],
)
async def get_evaluation_dimension_averages(
    evaluation_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return dimension-level averages aggregated across all groups for an evaluation."""

    dimensions = await controller.get_dimension_averages(evaluation_id)

    if dimensions is None:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    return dimensions


@router.get(
    "/{evaluation_id}/teachers/{teacher_id}/comments",
    response_model=TeacherCommentsOut,
)
async def get_teacher_comments(
    evaluation_id: int,
    teacher_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return comments grouped by course for a teacher within an evaluation."""

    result = await controller.get_teacher_comments(evaluation_id, teacher_id)

    if not result:
        raise HTTPException(
            status_code=404, detail="Evaluación o docente no encontrado"
        )

    return result


@router.get(
    "/{evaluation_id}/teachers/{teacher_id}/export",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            }
        },
    },
)
async def export_teacher_evaluation(
    evaluation_id: int,
    teacher_id: int,
    include_comments: bool = Depends(
        lambda x: x.query_params.get("include_comments", "false").lower() == "true"
    ),
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
    db: Session = Depends(get_db),
    stats_repo: StatsRepository = Depends(get_stats_repository),
):
    """Download an Excel report for a teacher's evaluation detail."""

    detail = await controller.get_teacher_detail(evaluation_id, teacher_id)
    if not detail:
        raise HTTPException(
            status_code=404, detail="Evaluación o docente no encontrado"
        )

    comparison = None
    eval_record = (
        db.query(EvaluationORM).filter(EvaluationORM.id == evaluation_id).first()
    )
    if eval_record:
        comparison = await stats_repo.get_teacher_vs_department(
            teacher_id, eval_record.academic_period_id
        )

    comments_by_course: dict[str, list] = {}
    if include_comments:
        comments_data = await controller.get_teacher_comments(evaluation_id, teacher_id)
        if comments_data:
            for c in comments_data["courses"]:
                key = f"{c['course_code']} - {c['course_name'] or ''}"
                comments_by_course[key] = c["comments"]

    buffer, filename = build_teacher_report(detail, comparison, comments_by_course)
    return teacher_streaming_response(buffer, filename)


@router.get(
    "/{evaluation_id}/teachers/{teacher_id}",
    response_model=TeacherEvaluationDetail,
)
async def get_teacher_evaluation_detail(
    evaluation_id: int,
    teacher_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return per-course and per-dimension scores for a teacher within an evaluation."""

    detail = await controller.get_teacher_detail(evaluation_id, teacher_id)

    if not detail:
        raise HTTPException(
            status_code=404, detail="Evaluación o docenten no encontrado"
        )

    return detail


@router.get(
    "/{evaluation_id}/export",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            }
        },
    },
)
async def export_evaluation(
    evaluation_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Download an Excel file with the department evaluation summary."""

    summary = await controller.get_summary(evaluation_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    buffer, filename = build_evaluation_report(summary)
    return evaluation_streaming_response(buffer, filename)


@router.post(
    "/{evaluation_id}/analyze",
    status_code=202,
    response_model=EvaluationOut,
)
async def analyze_evaluation(
    evaluation_id: int,
    background_tasks: BackgroundTasks,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Trigger AI classification of all comments for an evaluation."""

    evaluation = await controller.trigger_analysis(evaluation_id)

    background_tasks.add_task(analyze_evaluation_comments, evaluation_id)

    return evaluation


@router.delete(
    "/{evaluation_id}",
    response_model=EvaluationOut,
)
async def delete_evaluation(
    evaluation_id: int,
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Delete an evaluation and all related scores, comments, and data.
    Only the director of the associated department can perform this action."""

    evaluation = await controller.delete(evaluation_id, current_user)

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    return evaluation


@router.patch(
    "/{evaluation_id}/status",
    response_model=EvaluationOut,
)
async def update_evaluation_status(
    evaluation_id: int,
    payload: EvaluationStatusUpdate,
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Activate or deactivate an evaluation."""

    evaluation = await controller.update_status(
        evaluation_id, payload.active, current_user
    )

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    return evaluation
