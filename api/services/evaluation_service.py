"""Service for evaluation-related business operations."""

import os
import uuid
from math import ceil


from fastapi import HTTPException

from api.config import config
from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from api.models.department import DepartmentModel
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.directors import DirectorsRepository
from api.repositories.evaluations import EvaluationsRepository
from api.repositories.users import UsersRepository
from api.schemas.academic_period import AcademicPeriodCreate
from api.schemas.evaluation import EvaluationFilters
from api.schemas.pagination import build_paginated_response
from api.serializers.evaluations import evaluation_to_dict
from api.services.audit_service import AuditService
from api.utils.file_validation import validate_file_size
from api.utils.pdf_parser import parse_pdf


class EvaluationService:
    """Service for evaluation-related business operations."""

    def __init__(
        self,
        evaluations_repository: EvaluationsRepository,
        users_repository: UsersRepository,
        academic_periods_repository: AcademicPeriodsRepository,
        directors_repository: DirectorsRepository,
        audit_service: AuditService,
    ):
        self.evaluations_repository = evaluations_repository
        self.users_repository = users_repository
        self.academic_periods_repository = academic_periods_repository
        self.directors_repository = directors_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        user_email: str,
        filters: EvaluationFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all evaluations based on filters and pagination."""

        user_id = (
            self.users_repository.get_by_email(user_email).id if user_email else None
        )

        if not user_id:
            raise PermissionDeniedError(
                "Usuario no encontrado o no tiene permisos para acceder a las evaluaciones."
            )

        director = self.directors_repository.get_by_user_id(user_id)

        if not director:
            raise PermissionDeniedError(
                "El usuario no tiene permisos para acceder a las evaluaciones."
            )

        filters.department_id = director.department_id

        items, total = self.evaluations_repository.search(filters, pagination)

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, evaluation_id: int) -> dict | None:
        """Retrieve an evaluation by ID."""

        return self.evaluations_repository.get_by_id_as_dict(evaluation_id)

    async def get_by_period(self, period_id: int) -> dict | None:
        """Retrieve an evaluation by academic period ID."""

        return self.evaluations_repository.get_by_period_id(period_id)

    async def get_summary(self, evaluation_id: int) -> dict | None:
        """Get aggregated statistics for an evaluation."""

        return self.evaluations_repository.get_summary(evaluation_id)

    async def get_dimension_averages(self, evaluation_id: int) -> list[dict] | None:
        """Get dimension-level averages for an evaluation."""

        return self.evaluations_repository.get_dimension_averages(evaluation_id)

    async def get_teacher_detail(
        self, evaluation_id: int, teacher_id: int
    ) -> dict | None:
        """Get per-course and per-dimension detail for a teacher in an evaluation."""

        return self.evaluations_repository.get_teacher_detail(evaluation_id, teacher_id)

    async def get_teacher_comments(
        self, evaluation_id: int, teacher_id: int
    ) -> dict | None:
        """Get comments grouped by course for a teacher in an evaluation."""

        return self.evaluations_repository.get_teacher_comments(
            evaluation_id, teacher_id
        )

    async def get_teachers_by_period(
        self,
        academic_period_id: int,
        pagination: PaginationParams,
        search: str | None = None,
    ) -> dict | None:
        """Get all teachers with their average evaluation scores for a given academic period."""

        result = self.evaluations_repository.get_teachers_by_period(
            academic_period_id, pagination, search
        )

        if not result:
            return None

        total = result["teacher_count"]
        pages = ceil(total / pagination.limit) if total > 0 else 0

        return {
            **result,
            "page": pagination.page,
            "limit": pagination.limit,
            "pages": pages,
        }

    async def prepare_upload(
        self,
        filename: str | None,
        file_bytes: bytes,
        current_user: dict,
    ) -> tuple[dict, dict]:
        """Validate, parse, and persist an evaluation PDF upload.

        Returns (evaluation_dict, parsed_data) so the route can dispatch
        the background task with the parsed data.
        """

        if not filename or not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        validate_file_size(file_bytes)

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío",
            )

        try:
            parsed = parse_pdf(file_bytes)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}")

        if not parsed.get("period_code"):
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer el periodo académico del PDF",
            )

        if not parsed.get("department_code"):
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer el departamento del PDF",
            )

        if not parsed.get("teachers"):
            raise HTTPException(
                status_code=422,
                detail="No se encontraron datos del docente en el PDF. Asegúrese de que se trate de un documento de evaluación docente de la UFPS.",
            )

        period = self.academic_periods_repository.get_by_code(parsed["period_code"])

        if not period:
            period = self.academic_periods_repository.create(
                AcademicPeriodCreate(
                    code=parsed["period_code"],
                    name=parsed["period_code"],
                )
            )

        department = (
            self.evaluations_repository.db.query(DepartmentModel)
            .filter(DepartmentModel.code == parsed["department_code"])
            .first()
        )

        if not department:
            raise HTTPException(
                status_code=422,
                detail=f"Departamento '{
                    parsed['department_code']
                }' no está registrado en el sistema",
            )

        existing = self.evaluations_repository.get_by_period_and_department(
            period.id, department.id
        )

        if existing and existing["active"]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Una evaluación para el periodo '{parsed['period_code']}' "
                    f"y este departamento ya existe"
                ),
            )

        if existing and existing["status"] in ("PROCESSING", "FAILED"):
            self.evaluations_repository.delete_evaluation(existing["id"])

        eval_dir = os.path.join(
            config.UPLOAD_DIR,
            "evaluations",
            parsed["period_code"],
            parsed["department_code"],
        )
        os.makedirs(eval_dir, exist_ok=True)

        ext = os.path.splitext(filename or "evaluation.pdf")[1] or ".pdf"
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(eval_dir, stored_filename)

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        user_record = self.users_repository.get_by_uid(current_user["uid"])
        resolved_user_id = user_record.id if user_record else None

        evaluation_model = self.evaluations_repository.create_evaluation(
            user_id=resolved_user_id,
            academic_period_id=period.id,
            department_id=department.id,
            pdf_url=filepath,
            status="PROCESSING",
        )

        self.evaluations_repository.db.commit()

        await self.audit_service.log(
            action="CREATE",
            entity_name="evaluations",
            entity_id=evaluation_model.id,
            actor_id=resolved_user_id,
            description=f"""Se creó la evaluación {evaluation_model.id}
            del período {period.name} para el departamento {department.name} ({department.code})
            con un total de {len(parsed['teachers'])} docentes""",
        )

        return evaluation_to_dict(evaluation_model), parsed

    async def trigger_analysis(self, evaluation_id: int) -> dict:
        """Validate preconditions for triggering AI analysis.

        Returns the evaluation dict if preconditions are met.
        Raises HTTPException otherwise.
        """

        evaluation = self.evaluations_repository.get_by_id(evaluation_id)

        if not evaluation:
            raise ResourceNotFoundError("Evaluation", evaluation_id)

        if evaluation.status != "COMPLETED":
            raise ValidationError(
                "La evaluación todavía no ha sido procesada completamente"
            )

        if evaluation.ai_status == "ANALYZING":
            raise ValidationError(
                "El análisis de IA ya está en progreso para esta evaluación"
            )

        return evaluation_to_dict(evaluation)

    async def update_status(
        self, evaluation_id: int, active: bool, current_user: dict
    ) -> dict | None:
        """Activate or deactivate an evaluation."""

        evaluation = self.evaluations_repository.get_by_id_as_dict(evaluation_id)

        if not evaluation:
            return None

        updated = self.evaluations_repository.update_active_status(
            evaluation_id, active
        )

        action = "ACTIVATE" if active else "DEACTIVATE"
        user = self.users_repository.get_by_uid(current_user["uid"])

        await self.audit_service.log(
            action=action,
            entity_name="evaluations",
            entity_id=evaluation_id,
            actor_id=user.id if user else None,
            description=f"Se {'activó' if active else 'desactivó'} la evaluación {
                evaluation_id
            }",
        )

        return updated

    async def delete(self, evaluation_id: int, current_user: dict) -> dict | None:
        """Delete an evaluation. Only the director of the evaluation's department can delete."""

        evaluation = self.evaluations_repository.get_by_id(evaluation_id)

        if not evaluation:
            return None

        user = self.users_repository.get_by_uid(current_user["uid"])

        if not user:
            raise PermissionDeniedError()

        director = self.directors_repository.get_by_user_id(user.id)

        if not director or director.department_id != evaluation.department_id:
            raise PermissionDeniedError(
                "Solo el director del departamento asociado puede eliminar esta evaluación"
            )

        old_data = evaluation_to_dict(evaluation)
        self.evaluations_repository.delete_evaluation(evaluation_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="evaluations",
            entity_id=evaluation_id,
            actor_id=user.id,
            description=f"Se eliminó la evaluación {evaluation_id} del período {
                old_data.get('academic_period_code') or 'N/A'
            }",
        )

        return old_data
