"""Service for evaluation-related business operations."""

import os
from math import ceil

from fastapi import HTTPException

from api.config import config
from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.directors import DirectorsRepository
from api.repositories.evaluations import EvaluationsRepository
from api.repositories.users import UsersRepository
from api.schemas.academic_period import AcademicPeriodCreate
from api.schemas.evaluation import EvaluationFilters, UploadedPdf
from api.schemas.pagination import build_paginated_response
from api.schemas.user import RoleName
from api.serializers.evaluations import evaluation_to_dict
from api.services.audit_service import AuditService
from api.utils.evaluation_pdfs import (
    join_pdf_urls,
    select_pdf_url,
    stored_pdf_filename,
)
from api.utils.file_validation import validate_file_size
from api.utils.modalities import modality_label, validated_modality
from api.utils.pdf_parser import merge_parsed_evaluations, parse_pdf

# Un PDF por modalidad: presencial y a distancia.
MAX_EVALUATION_PDFS = 2

PDF_MAGIC_BYTES = b"%PDF-"


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

    async def get_by_id(
        self, evaluation_id: int, modality: str | None = None
    ) -> dict | None:
        """Retrieve an evaluation by ID, including its pedagogical dimension averages
        and a comparison against the department's evaluation in the previous period.

        With a `modality`, every figure — average, dimensions, risk counts,
        teacher count and the previous-period comparison — is computed over
        the groups of that kind of program only. Without it they cover the
        whole evaluation, presencial and a distancia together."""

        modality = validated_modality(modality)

        evaluation = self.evaluations_repository.get_by_id_as_dict(
            evaluation_id, modality
        )

        if not evaluation:
            return None

        evaluation["modality"] = modality
        evaluation["dimension_averages"] = (
            self.evaluations_repository.get_dimension_averages(evaluation_id, modality)
        )
        evaluation["comparison"] = self._get_previous_period_comparison(
            evaluation, modality
        )

        return evaluation

    def _get_previous_period_comparison(
        self, evaluation: dict, modality: str | None = None
    ) -> dict | None:
        """Compare `evaluation` against the same department's evaluation in the
        academic period immediately before it (e.g. "2025-2" -> "2025-1").

        A `modality` restricts both sides of the comparison to that kind of
        program, so presencial is never compared against a distancia average.

        Returns None if there is no previous period or no evaluation for the
        department there.
        """

        period_code = evaluation.get("academic_period_code")
        department_id = evaluation.get("department_id")

        if not period_code or department_id is None:
            return None

        prev_code = self.academic_periods_repository.get_previous_period_code(
            period_code
        )
        if not prev_code:
            return None

        prev_period = self.academic_periods_repository.get_by_code(prev_code)
        if not prev_period:
            return None

        prev_evaluation = self.evaluations_repository.get_by_period_and_department(
            prev_period.id, department_id
        )
        if not prev_evaluation:
            return None

        prev_evaluation = self.evaluations_repository.get_by_id_as_dict(
            prev_evaluation["id"], modality
        )
        prev_dimensions = self.evaluations_repository.get_dimension_averages(
            prev_evaluation["id"], modality
        )

        current_avg = evaluation.get("overall_average")
        old_avg = prev_evaluation.get("overall_average")

        return {
            "previous_period_code": prev_period.code,
            "previous_period_name": prev_period.name,
            "current_average": current_avg,
            "old_average": old_avg,
            "average_difference": (
                round(current_avg - old_avg, 2)
                if current_avg is not None and old_avg is not None
                else None
            ),
            "dimensions": self._diff_dimensions(
                evaluation["dimension_averages"], prev_dimensions
            ),
        }

    @staticmethod
    def _diff_dimensions(
        current_dimensions: list[dict], old_dimensions: list[dict]
    ) -> list[dict]:
        """Merge two `get_dimension_averages()` results into a current-vs-old diff,
        matching dimensions and questions by name/code."""

        old_by_name = {d["dimension"]: d for d in old_dimensions}
        comparison = []

        for dim in current_dimensions:
            old_dim = old_by_name.get(dim["dimension"])
            old_avg = old_dim["average"] if old_dim else None
            old_questions = (
                {q["code"]: q["score"] for q in old_dim["questions"]} if old_dim else {}
            )

            questions = []
            for q in dim["questions"]:
                old_score = old_questions.get(q["code"])
                questions.append(
                    {
                        "code": q["code"],
                        "text": q["text"],
                        "current_average": q["score"],
                        "old_average": old_score,
                        "difference": (
                            round(q["score"] - old_score, 2)
                            if old_score is not None
                            else None
                        ),
                    }
                )

            comparison.append(
                {
                    "dimension": dim["dimension"],
                    "current_average": dim["average"],
                    "old_average": old_avg,
                    "difference": (
                        round(dim["average"] - old_avg, 2)
                        if dim["average"] is not None and old_avg is not None
                        else None
                    ),
                    "questions": questions,
                }
            )

        return comparison

    async def get_by_period(self, period_id: int) -> dict | None:
        """Retrieve an evaluation by academic period ID."""

        return self.evaluations_repository.get_by_period_id(period_id)

    async def get_pdf_path(
        self,
        evaluation_id: int,
        current_user: dict,
        modality: str | None = None,
    ) -> str:
        """Return the absolute path to an evaluation's PDF on disk.

        An evaluation can be backed by the presencial and the distancia
        documents; `modality` picks one of them, and without it the first one
        is served. Only ADMIN or the DIRECTOR of the department the evaluation
        belongs to may access the file."""

        evaluation = self.evaluations_repository.get_by_id_as_dict(evaluation_id)

        if not evaluation:
            raise ResourceNotFoundError("evaluation", evaluation_id)

        roles = set(current_user.get("roles", []))
        is_admin = RoleName.ADMIN.value in roles
        is_department_director = (
            RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles
            and evaluation.get("department_id") is not None
            and evaluation.get("department_id") == current_user.get("department_id")
        )

        if not (is_admin or is_department_director):
            raise PermissionDeniedError(
                "No tiene permiso para acceder al PDF de esta evaluación"
            )

        pdf_url = evaluation.get("pdf_url")

        if not pdf_url:
            raise ResourceNotFoundError("evaluation pdf", evaluation_id)

        pdf_path = select_pdf_url(pdf_url, validated_modality(modality))

        if not pdf_path:
            raise ResourceNotFoundError("evaluation pdf", evaluation_id)

        return pdf_path

    async def get_summary(self, evaluation_id: int) -> dict | None:
        """Get aggregated statistics for an evaluation."""

        return self.evaluations_repository.get_summary(evaluation_id)

    async def get_dimension_averages(self, evaluation_id: int) -> list[dict] | None:
        """Get dimension-level averages for an evaluation."""

        return self.evaluations_repository.get_dimension_averages(evaluation_id)

    async def get_dimension_detail(
        self,
        evaluation_id: int,
        current_user: dict,
        teacher_id: int | None = None,
        course_id: int | None = None,
        modality: str | None = None,
    ) -> dict | None:
        """Get an evaluation's pedagogical dimensions with per-question averages,
        optionally restricted to a single teacher and/or course (materia), and
        scoped to one modality.

        Only the director of the evaluation's department may access it."""

        evaluation = self.evaluations_repository.get_by_id(evaluation_id)

        if not evaluation:
            return None

        user = self.users_repository.get_by_uid(current_user["uid"])

        if not user:
            raise PermissionDeniedError()

        director = self.directors_repository.get_by_user_id(user.id)

        if not director or director.department_id != evaluation.department_id:
            raise PermissionDeniedError(
                "Solo el director del departamento asociado puede consultar el "
                "detalle de dimensiones de esta evaluación"
            )

        return self.evaluations_repository.get_dimension_detail(
            evaluation_id, teacher_id, course_id, validated_modality(modality)
        )

    async def get_teacher_detail(
        self,
        period_name: str,
        teacher_id: int,
        department_id: int | None = None,
        compare_previous: bool = False,
    ) -> dict | None:
        """Get per-course and per-dimension detail for a teacher in an evaluation.

        If `compare_previous` is True, the returned dict also includes a
        `previous_period` key with the same detail for the semester immediately
        before `period_name` (e.g. "2025-2" -> "2025-1"), or None if there is
        no evaluation for that teacher in that period.
        """

        period = self.academic_periods_repository.get_by_name(period_name)
        if not period:
            return None

        if department_id is not None:
            evaluation_data = self.evaluations_repository.get_by_period_and_department(
                period.id, department_id
            )
        else:
            evaluation_data = self.evaluations_repository.get_by_period_id(period.id)

        if not evaluation_data:
            return None

        detail = self.evaluations_repository.get_teacher_detail(
            evaluation_data["id"], teacher_id
        )

        if detail and compare_previous:
            detail["previous_period"] = self._get_previous_period_detail(
                period, teacher_id, department_id
            )

        return detail

    def _get_previous_period_detail(
        self, period, teacher_id: int, department_id: int | None
    ) -> dict | None:
        """Get a teacher's evaluation detail for the semester right before `period`."""

        prev_code = self.academic_periods_repository.get_previous_period_code(
            period.code
        )

        if not prev_code:
            return None

        prev_period = self.academic_periods_repository.get_by_code(prev_code)

        if not prev_period:
            return None

        if department_id is not None:
            prev_evaluation_data = (
                self.evaluations_repository.get_by_period_and_department(
                    prev_period.id, department_id
                )
            )
        else:
            prev_evaluation_data = self.evaluations_repository.get_by_period_id(
                prev_period.id
            )

        if not prev_evaluation_data:
            return None

        return self.evaluations_repository.get_teacher_detail(
            prev_evaluation_data["id"], teacher_id
        )

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
        uploads: list[UploadedPdf],
        current_user: dict,
    ) -> tuple[dict, dict]:
        """Validate, parse, and persist the PDFs of an evaluation.

        The university publishes one document per kind of program, so a
        director uploads either a single PDF or the presencial and the
        distancia ones together. Both describe the same period and department
        and are stored side by side under a single evaluation.

        Returns (evaluation_dict, parsed_data) so the route can dispatch
        the background task with the merged parsed data.
        """

        documents = self._parse_uploads(uploads)
        parsed_documents = [parsed for _, parsed in documents]
        parsed = merge_parsed_evaluations(parsed_documents)

        period = self.academic_periods_repository.get_by_code(parsed["period_code"])

        if not period:
            period = self.academic_periods_repository.create(
                AcademicPeriodCreate(
                    code=parsed["period_code"],
                    name=parsed["period_code"],
                )
            )

        department = self.evaluations_repository.get_department_by_code(
            parsed["department_code"]
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

        filepaths = self._store_uploads(
            documents, parsed["period_code"], parsed["department_code"]
        )

        user_record = self.users_repository.get_by_uid(current_user["uid"])
        resolved_user_id = user_record.id if user_record else None

        evaluation_model = self.evaluations_repository.create_evaluation(
            user_id=resolved_user_id,
            academic_period_id=period.id,
            department_id=department.id,
            pdf_url=join_pdf_urls(filepaths),
            status="PROCESSING",
        )

        self.evaluations_repository.db.commit()

        modalities = ", ".join(
            modality_label(document["modality"]) for _, document in documents
        )

        await self.audit_service.log(
            action="CREATE",
            entity_name="evaluations",
            entity_id=evaluation_model.id,
            actor_id=resolved_user_id,
            description=f"""Se creó la evaluación {evaluation_model.id}
            del período {period.name} para el departamento {department.name} ({department.code})
            con un total de {len(parsed['teachers'])} docentes
            a partir de {len(documents)} PDF(s) ({modalities})""",
        )

        return evaluation_to_dict(evaluation_model), parsed

    def _parse_uploads(
        self, uploads: list[UploadedPdf]
    ) -> list[tuple[UploadedPdf, dict]]:
        """Validate every uploaded file and return it next to its parsed content.

        Rejects anything that is not a UFPS evaluation report, and the
        combinations that cannot belong to a single evaluation: documents of
        different periods or departments, and two documents of the same
        modality."""

        if not uploads:
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el PDF de la evaluación",
            )

        if len(uploads) > MAX_EVALUATION_PDFS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Solo puede subir hasta {MAX_EVALUATION_PDFS} PDFs por "
                    "evaluación: el de programas presenciales y el de programas "
                    "a distancia"
                ),
            )

        documents = [(upload, self._parse_upload(upload)) for upload in uploads]

        periods = {parsed["period_code"] for _, parsed in documents}

        if len(periods) > 1:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Los PDFs pertenecen a periodos académicos distintos "
                    f"({', '.join(sorted(periods))}); deben ser del mismo periodo"
                ),
            )

        departments = {parsed["department_code"] for _, parsed in documents}

        if len(departments) > 1:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Los PDFs pertenecen a departamentos distintos "
                    f"({', '.join(sorted(departments))}); deben ser del mismo "
                    "departamento"
                ),
            )

        modalities = [parsed["modality"] for _, parsed in documents]

        if len(modalities) > len(set(modalities)):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Los dos PDFs corresponden a la misma modalidad "
                    f"({modality_label(modalities[0])}); suba uno de programas "
                    "presenciales y uno de programas a distancia"
                ),
            )

        return documents

    def _parse_upload(self, upload: UploadedPdf) -> dict:
        """Validate a single uploaded file and return its parsed content."""

        name = upload.filename or "el archivo"

        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"'{name}' no es un archivo PDF"
            )

        if not upload.content:
            raise HTTPException(status_code=400, detail=f"'{name}' está vacío")

        validate_file_size(upload.content)

        if not upload.content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail=f"'{name}' no es un PDF válido o está dañado",
            )

        try:
            parsed = parse_pdf(upload.content)
        except Exception as exc:
            print(f"Error parsing PDF: {exc}")
            raise HTTPException(
                status_code=400, detail=f"Error al procesar '{name}': {exc}"
            )

        if not parsed.get("period_code"):
            raise HTTPException(
                status_code=422,
                detail=f"No se pudo extraer el periodo académico de '{name}'",
            )

        if not parsed.get("department_code"):
            raise HTTPException(
                status_code=422,
                detail=f"No se pudo extraer el departamento de '{name}'",
            )

        if not parsed.get("modality"):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No se pudo determinar si '{name}' corresponde a programas "
                    "presenciales o a distancia. Asegúrese de subir el reporte "
                    "completo, tal como lo genera la universidad"
                ),
            )

        if not parsed.get("teachers"):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No se encontraron datos de docentes en '{name}'. Asegúrese "
                    "de que se trate de un documento de evaluación docente de la UFPS"
                ),
            )

        return parsed

    def _store_uploads(
        self,
        documents: list[tuple[UploadedPdf, dict]],
        period_code: str,
        department_code: str,
    ) -> list[str]:
        """Write the uploaded PDFs to disk and return their paths."""

        eval_dir = os.path.join(
            config.UPLOAD_DIR,
            "evaluations",
            period_code,
            department_code,
        )
        os.makedirs(eval_dir, exist_ok=True)

        filepaths = []

        for upload, parsed in documents:
            filepath = os.path.join(eval_dir, stored_pdf_filename(parsed["modality"]))

            with open(filepath, "wb") as f:
                f.write(upload.content)

            filepaths.append(filepath)

        return filepaths

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
