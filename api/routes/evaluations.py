"""
Routes for evaluation operations.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.controllers.evaluations import EvaluationsController, get_evaluations_controller
from api.database import get_db
from api.middlewares.auth import require_roles
from api.models.academic_period import AcademicPeriodModel
from api.models.department import DepartmentModel
from api.repositories.evaluations import EvaluationsRepository, get_evaluations_repository
from api.schemas.evaluation import EvaluationDetailResponse, EvaluationListResponse
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName
from api.utils.evaluation_processor import process_evaluation
from api.utils.pdf_parser import parse_pdf

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "/upload",
    status_code=202,
    response_model=EvaluationDetailResponse,
    responses={
        400: {"model": ResponseSchema},
        409: {"model": ResponseSchema},
        422: {"model": ResponseSchema},
    },
)
async def upload_evaluation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])
    ),
    db: Session = Depends(get_db),
    evaluations_repo: EvaluationsRepository = Depends(get_evaluations_repository),
):
    """Upload a teacher evaluation PDF for a department.

    Parses the document immediately to validate period and department, then
    processes scores and comments in the background. Returns 202 with the
    evaluation record while processing continues.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_bytes = await file.read()

    try:
        parsed = parse_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}")

    if not parsed.get("period_code"):
        raise HTTPException(
            status_code=422, detail="Could not extract academic period from PDF"
        )
    if not parsed.get("department_code"):
        raise HTTPException(
            status_code=422, detail="Could not extract department from PDF"
        )

    period = (
        db.query(AcademicPeriodModel)
        .filter(AcademicPeriodModel.code == parsed["period_code"])
        .first()
    )
    if not period:
        raise HTTPException(
            status_code=422,
            detail=f"Academic period '{parsed['period_code']}' is not registered in the system",
        )

    department = (
        db.query(DepartmentModel)
        .filter(DepartmentModel.code == parsed["department_code"])
        .first()
    )
    if not department:
        raise HTTPException(
            status_code=422,
            detail=f"Department '{parsed['department_code']}' is not registered in the system",
        )

    existing = await evaluations_repo.get_by_period_and_department(period.id, department.id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"An evaluation for period '{parsed['period_code']}' "
                "and this department already exists"
            ),
        )

    evaluation = await evaluations_repo.create(
        user_id=current_user["uid"],
        academic_period_id=period.id,
        department_id=department.id,
        pdf_url="",
        status="PROCESSING",
    )

    background_tasks.add_task(process_evaluation, evaluation["id"], parsed)

    return ResponseSchema(
        status=202,
        message="Evaluation upload started. Processing in background.",
        data=evaluation,
        path="/evaluations/upload",
    )


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
