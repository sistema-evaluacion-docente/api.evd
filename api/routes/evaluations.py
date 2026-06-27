"""
Routes for evaluation operations.
"""

import io
import os
import uuid

import openpyxl
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.config import config
from api.controllers.evaluations import (
    EvaluationsController,
    get_evaluations_controller,
)
from api.database import get_db
from api.middlewares.auth import get_current_user, require_roles
from api.models.academic_period import AcademicPeriodModel
from api.models.department import DepartmentModel
from api.repositories.evaluations import (
    EvaluationsRepository,
    get_evaluations_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.evaluation import (
    EvaluationDetailResponse,
    EvaluationListResponse,
    EvaluationStatusUpdate,
)
from api.schemas.evaluation_summary import EvaluationSummaryResponse
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
    users_repo: UsersRepository = Depends(get_users_repository),
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

    if not parsed.get("teachers"):
        raise HTTPException(
            status_code=422,
            detail="No teacher data found in PDF. Make sure it is a UFPS teacher evaluation document.",
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

    existing = await evaluations_repo.get_by_period_and_department(
        period.id, department.id
    )

    if existing and existing["active"] and existing["status"] == "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=(
                f"An evaluation for period '{parsed['period_code']}' "
                "and this department already exists"
            ),
        )

    if existing and existing["status"] in ("PROCESSING", "FAILED"):
        await evaluations_repo.delete(existing["id"])

    eval_dir = os.path.join(
        config.UPLOAD_DIR,
        "evaluations",
        parsed["period_code"],
        parsed["department_code"],
    )
    os.makedirs(eval_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "evaluation.pdf")[1] or ".pdf"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(eval_dir, filename)

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    user_record = await users_repo.get_by_uid(current_user["uid"])
    resolved_user_id = user_record["id"] if user_record else None

    evaluation = await evaluations_repo.create(
        user_id=resolved_user_id,
        academic_period_id=period.id,
        department_id=department.id,
        pdf_url=filepath,
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


@router.get(
    "/{evaluation_id}/summary",
    response_model=EvaluationSummaryResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_evaluation_summary(
    evaluation_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Return aggregated department statistics for an evaluation: department average,
    teacher ranking, and best/worst teacher identification."""

    summary = await controller.get_summary(evaluation_id)

    if not summary:
        return ResponseSchema(
            status=404,
            message="Evaluation not found",
            path=f"/evaluations/{evaluation_id}/summary",
        )

    return ResponseSchema(
        status=200,
        message="Summary generated successfully",
        data=summary,
        path=f"/evaluations/{evaluation_id}/summary",
    )


@router.get(
    "/{evaluation_id}/export",
    responses={
        200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}},
        403: {"description": "Forbidden"},
        404: {"model": ResponseSchema},
    },
)
async def export_evaluation(
    evaluation_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Download an Excel file with the department evaluation summary."""

    summary = await controller.get_summary(evaluation_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen Evaluación Docente"

    ws.append(["Ranking", "Nombre", "Código", "Tipo Contrato", "Grupos Evaluados", "Promedio"])

    for item in summary["ranking"]:
        ws.append([
            item["rank"],
            item["name"] or "",
            item["institutional_code"],
            item["contract_type"] or "",
            item["group_count"],
            item["overall_average"],
        ])

    ws.append([])
    ws.append(["", "Promedio Departamento", "", "", "", summary["department_average"]])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"evaluacion_{summary['period_code']}_{evaluation_id}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch(
    "/{evaluation_id}/status",
    response_model=EvaluationDetailResponse,
    responses={
        400: {"model": ResponseSchema},
        403: {"description": "Forbidden"},
        404: {"model": ResponseSchema},
    },
)
async def update_evaluation_status(
    evaluation_id: int,
    payload: EvaluationStatusUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: EvaluationsController = Depends(get_evaluations_controller),
):
    """Activate or deactivate an evaluation."""

    evaluation = await controller.update_status(
        evaluation_id, payload.active, current_user
    )

    if not evaluation:
        return ResponseSchema(
            status=404,
            message="Evaluation not found",
            path=f"/evaluations/{evaluation_id}/status",
        )

    action = "activated" if payload.active else "deactivated"

    return ResponseSchema(
        status=200,
        message=f"Evaluation {action} successfully",
        data=evaluation,
        path=f"/evaluations/{evaluation_id}/status",
    )
