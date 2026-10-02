"""Service for teacher-related business operations."""

import csv
import io
import unicodedata

import openpyxl

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceAlreadyExistsError, ResourceNotFoundError, ValidationError
from api.utils.modalities import validated_modality
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.evaluations import EvaluationsRepository
from api.repositories.stats import StatsRepository
from api.repositories.teachers import TeachersRepository
from api.repositories.users import UsersRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)
from api.schemas.user import RoleName, TokenUser, UserCreate
from api.serializers.teachers import teacher_to_dict
from api.serializers.users import user_to_dict
from api.services.audit_service import AuditService
from api.services.user_service import UserService
from api.utils.institutional_codes import code_key

INSTITUTIONAL_EMAIL_DOMAIN = "@ufps.edu.co"

# Accepted (normalized) header names for the teacher email import.
_CODE_HEADERS = {"codigo", "codigo institucional"}
_EMAIL_HEADERS = {"correo", "email", "correo institucional", "correo electronico"}


class TeacherService:
    """Service for teacher-related business operations."""

    def __init__(
        self,
        teachers_repository: TeachersRepository,
        users_repository: UsersRepository,
        audit_service: AuditService,
        academic_periods_repository: AcademicPeriodsRepository,
        user_service: UserService,
        stats_repository: StatsRepository | None = None,
        evaluations_repository: EvaluationsRepository | None = None,
    ):
        self.teachers_repository = teachers_repository
        self.users_repository = users_repository
        self.audit_service = audit_service
        self.stats_repository = stats_repository
        self.academic_periods_repository = academic_periods_repository
        self.user_service = user_service
        self.evaluations_repository = evaluations_repository

    async def get_all(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all teachers based on filters and pagination."""

        teachers, total = self.teachers_repository.search(filters, pagination)

        roles_by_user = self.users_repository.get_user_role_names_bulk(
            [t.user_id for t in teachers if t.user_id]
        )
        items = [
            self._enrich_teacher_to_dict(t, roles=roles_by_user.get(t.user_id, []))
            for t in teachers
        ]

        return build_paginated_response(items, total, pagination)

    async def get_all_with_averages(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
        academic_period_id: int,
        has_average: bool = True,
        modality: str | None = None,
    ) -> dict:
        """Retrieve teachers with overall_average for a given academic period.

        A `modality` restricts the average and the high-risk comment count to
        the groups of that kind of program."""

        rows, total = self.teachers_repository.search_with_averages(
            filters,
            pagination,
            academic_period_id,
            has_average,
            validated_modality(modality),
        )

        roles_by_user = self.users_repository.get_user_role_names_bulk(
            [teacher.user_id for teacher, _, _ in rows if teacher.user_id]
        )

        items = []

        for teacher, avg_score, high_risk_count in rows:
            d = self._enrich_teacher_to_dict(
                teacher, roles=roles_by_user.get(teacher.user_id, [])
            )
            d["overall_average"] = float(avg_score) if avg_score is not None else None
            d["high_risk_comments_count"] = int(high_risk_count or 0)

            items.append(d)

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, teacher_id: int) -> dict | None:
        """Retrieve a teacher by ID."""

        teacher = self.teachers_repository.get_by_id(teacher_id)

        if not teacher:
            return None

        return self._enrich_teacher_to_dict(teacher)

    async def create(self, data: TeacherCreate, current_user: dict) -> dict:
        """Create a new teacher, rejecting duplicate institutional codes."""

        existing = self.teachers_repository.get_by_institutional_code(
            data.institutional_code
        )

        if existing:
            raise ResourceAlreadyExistsError(
                "teacher", "institutional_code", data.institutional_code
            )

        user_data = UserCreate(
            email=f"{data.institutional_code}@temp.local",
            name=data.institutional_code,
            active=True,
            institutional_code=data.institutional_code,
            contract_type=data.contract_type,
        )

        user = await self.user_service.create_user_with_roles(
            user_data, department_id=data.department_id
        )

        teacher = self.teachers_repository.get_by_institutional_code(
            data.institutional_code
        )

        result = self._enrich_teacher_to_dict(teacher)

        await self.audit_service.log(
            action="CREATE",
            entity_name="teachers",
            entity_id=teacher.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el profesor con código {data.institutional_code}, "
                f"departamento {data.department_id}, "
                f"tipo contrato: {data.contract_type}"
            ),
        )

        return result

    async def create_with_user(
        self, data: TeacherCreateWithUser, current_user: dict
    ) -> dict:
        """Create a user and then a teacher linked to that user."""

        existing = self.teachers_repository.get_by_institutional_code(
            data.institutional_code
        )

        if existing:
            raise ResourceAlreadyExistsError(
                "teacher", "institutional_code", data.institutional_code
            )

        existing_user = self.users_repository.get_by_email(data.email)

        if existing_user:
            raise ResourceAlreadyExistsError("user", "email", data.email)

        user_data = UserCreate(
            email=data.email,
            name=data.name,
            active=data.active,
            institutional_code=data.institutional_code,
            contract_type=data.contract_type,
        )

        await self.user_service.create_user_with_roles(
            user_data, department_id=data.department_id
        )

        teacher = self.teachers_repository.get_by_institutional_code(
            data.institutional_code
        )

        result = self._enrich_teacher_to_dict(teacher)

        await self.audit_service.log(
            action="CREATE",
            entity_name="teachers",
            entity_id=result.get("id"),
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el profesor con código {data.institutional_code}, "
                f"departamento {data.department_id}, "
                f"tipo contrato: {data.contract_type}, "
                f"usuario: {data.email}"
            ),
        )

        return result

    async def update(
        self, teacher_id: int, data: TeacherUpdate, current_user: dict
    ) -> dict | None:
        """Update a teacher's fields."""

        teacher = self.teachers_repository.get_by_id(teacher_id)

        if not teacher:
            return None

        old_data = teacher_to_dict(teacher)
        old_user_data = (
            {
                "name": teacher.user.name,
                "email": teacher.user.email,
                "avatar_url": teacher.user.avatar_url,
                "institutional_code": teacher.user.institutional_code,
            }
            if teacher.user
            else {}
        )
        payload = data.model_dump(exclude_unset=True)
        institutional_code = payload.pop("institutional_code", None)

        user_changes = {}
        for field in ("name", "email", "avatar_url"):
            if field in payload and teacher.user:
                user_changes[field] = payload.pop(field)

        updated = self.teachers_repository.update_teacher(teacher, payload)

        if user_changes and teacher.user:
            for field, value in user_changes.items():
                setattr(teacher.user, field, value)
            self.teachers_repository.db.commit()
            self.teachers_repository.db.refresh(teacher.user)

        if institutional_code is not None and teacher.user:
            teacher.user.institutional_code = institutional_code
            self.teachers_repository.db.commit()
            self.teachers_repository.db.refresh(teacher.user)

        result = self._enrich_teacher_to_dict(updated)

        changes = []
        for field in (
            "department_id",
            "contract_type",
            "user_id",
            "active",
        ):
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        for field in ("name", "email", "avatar_url"):
            new_val = user_changes.get(field)
            if new_val is not None and new_val != old_user_data.get(field):
                old_val = old_user_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        if institutional_code is not None and institutional_code != old_data.get(
            "institutional_code"
        ):
            changes.append(
                f"institutional_code cambió de {old_data.get('institutional_code')} a {institutional_code}"
            )

        desc = f"Se actualizó el profesor #{teacher_id}"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="teachers",
            entity_id=teacher_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return result

    async def delete(self, teacher_id: int, current_user: dict) -> dict | None:
        """Delete a teacher by ID."""

        teacher = self.teachers_repository.get_by_id(teacher_id)

        if not teacher:
            return None

        old_data = teacher_to_dict(teacher)

        self.teachers_repository.delete_teacher(teacher_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="teachers",
            entity_id=teacher_id,
            actor_id=current_user.get("id"),
            description=f"Se eliminó el profesor con código {old_data.get('institutional_code')}",
        )

        return old_data

    async def count_by_department(
        self, department_id: int, academic_period_id: int
    ) -> dict:
        """Count teachers in a department for current and previous period."""

        period = await self.academic_periods_repository.get_by_id(academic_period_id)

        previous_period_id = None
        if period:
            prev_code = await self.academic_periods_repository.get_previous_period_code(
                period["code"]
            )
            if prev_code:
                prev_period = await self.academic_periods_repository.get_by_code(
                    prev_code
                )
                if prev_period:
                    previous_period_id = prev_period["id"]

        return self.teachers_repository.count_by_department(
            department_id, academic_period_id, previous_period_id
        )

    async def get_history(
        self,
        current_user: TokenUser,
        teacher_id: int,
        pagination: PaginationParams,
        sort_by: str | None = None,
    ) -> dict | None:
        """Get teacher's historical averages across all periods, paginated."""

        user = self.users_repository.get_by_uid(current_user.uid)
        teacher = self.teachers_repository.get_by_id(teacher_id)
        roles = self.users_repository.get_user_role_names(user.id) if user else []

        if not user or not teacher:
            raise ValidationError("Usuario no encontrado")

        is_admin = RoleName.ADMIN in roles
        is_own_teacher = RoleName.DOCENTE in roles and teacher.user_id == user.id
        is_department_director = False

        if RoleName.DIRECTOR_DE_DEPARTAMENTO in roles:
            director = self.users_repository.get_director_by_user_id(user.id)
            is_department_director = bool(
                director and director.department_id == teacher.department_id
            )

        if not (is_admin or is_own_teacher or is_department_director):
            raise PermissionDeniedError("No tiene permiso para acceder a este historial")

        items, total, teacher_info = self.teachers_repository.get_history(
            teacher_id, pagination, sort_by
        )

        if teacher_info is None:
            return None

        paginated = build_paginated_response(items, total, pagination)

        return {**teacher_info, **paginated}

    async def get_course_history(
        self,
        current_user: TokenUser,
        teacher_id: int,
        course_code: str,
        limit: int | None = None,
    ) -> dict | None:
        """Get per-period history for a teacher's course."""

        user = self.users_repository.get_by_uid(current_user.uid)
        teacher = self.teachers_repository.get_by_id(teacher_id)
        roles = self.users_repository.get_user_role_names(user.id) if user else []

        if not user or not teacher:
            raise ValidationError("Usuario no encontrado")

        is_admin = RoleName.ADMIN in roles
        is_own_teacher = RoleName.DOCENTE in roles and teacher.user_id == user.id
        is_department_director = False

        if RoleName.DIRECTOR_DE_DEPARTAMENTO in roles:
            director = self.users_repository.get_director_by_user_id(user.id)
            is_department_director = bool(
                director and director.department_id == teacher.department_id
            )

        if not (is_admin or is_own_teacher or is_department_director):
            raise PermissionDeniedError("No tiene permiso para ver el historial de este docente")

        return self.stats_repository.get_course_history(
            teacher_id, course_code, teacher.department_id, limit
        )

    async def get_evaluation_report(
        self, teacher_id: int, evaluation_id: int, current_user: TokenUser
    ) -> bytes:
        """Return a PDF with only the pages belonging to the teacher in the evaluation.

        DOCENTE may only access their own report; DIRECTOR may access any
        teacher in their department. Every way of not finding the report raises
        ``ResourceNotFoundError``, which the global handler turns into the 404 —
        so there is no ``None`` for the route to translate.
        """
        from api.utils.evaluation_pdfs import split_pdf_urls
        from api.utils.pdf_extractor import extract_teacher_pages

        user = self.users_repository.get_by_uid(current_user.uid)
        teacher = self.teachers_repository.get_by_id(teacher_id)

        if not user or not teacher:
            raise ResourceNotFoundError("Docente", teacher_id)

        roles = self.users_repository.get_user_role_names(user.id)

        is_own_teacher = RoleName.DOCENTE in roles and teacher.user_id == user.id
        is_department_director = False

        if RoleName.DIRECTOR_DE_DEPARTAMENTO in roles:
            director = self.users_repository.get_director_by_user_id(user.id)
            is_department_director = bool(
                director and director.department_id == teacher.department_id
            )

        if not (is_own_teacher or is_department_director):
            raise PermissionDeniedError(
                "No tiene permiso para acceder al reporte de este docente"
            )

        if not self.evaluations_repository:
            raise ValidationError("Repositorio de evaluaciones no disponible")

        evaluation = self.evaluations_repository.get_by_id(evaluation_id)
        if not evaluation:
            raise ResourceNotFoundError("Evaluación", evaluation_id)

        pdf_paths = split_pdf_urls(evaluation.pdf_url)
        if not pdf_paths:
            raise ResourceNotFoundError("PDF de la evaluación", evaluation_id)

        if not teacher.user or not teacher.user.institutional_code:
            raise ResourceNotFoundError(
                "Código institucional del docente", teacher_id
            )

        pdf_bytes = extract_teacher_pages(pdf_paths, teacher.user.institutional_code)

        if pdf_bytes is None:
            raise ResourceNotFoundError(
                "Docente en el PDF de la evaluación", teacher_id
            )

        return pdf_bytes

    async def upload_excel(
        self, file_bytes: bytes, filename: str, department_id: int, current_user: dict
    ) -> dict:
        """Import the institutional email of the department's teachers from a
        CSV/XLSX with two columns: ``codigo`` and ``correo`` (``email`` works
        too; any other column is ignored).

        A teacher first seen in an evaluation PDF is created with a placeholder
        ``{código}@temp.local`` email and cannot log in until it is replaced —
        that is what this import does, matching rows by institutional code:

        - unknown code: the teacher is created in the director's department,
          named after the code until their evaluation fills the real name;
        - known code, never logged in: the email is replaced;
        - known code, already logged in: the email is kept and reported;
        - a teacher of another department is left untouched and reported.

        Everything is decided first and written in a single commit.
        """

        is_csv = filename.lower().endswith(".csv")
        rows = self._parse_csv(file_bytes) if is_csv else self._parse_excel(file_bytes)

        if len(rows) < 2:
            file_type = "CSV" if is_csv else "Excel"
            raise ValidationError(
                f"El archivo {file_type} debe contener al menos un encabezado y una fila de datos"
            )

        header = [self._normalize_header(cell) for cell in rows[0]]
        code_col = next((i for i, h in enumerate(header) if h in _CODE_HEADERS), None)
        email_col = next((i for i, h in enumerate(header) if h in _EMAIL_HEADERS), None)

        if code_col is None or email_col is None:
            raise ValidationError(
                "El archivo debe tener las columnas 'codigo' y 'correo'"
            )

        entries = []
        for row_number, row in enumerate(rows[1:], start=2):
            code = self._cell_text(row, code_col)
            email = self._cell_text(row, email_col).lower()

            if code or email:
                entries.append((row_number, code, email))

        users_by_code = self.users_repository.get_by_institutional_codes(
            [code for _, code, _ in entries if code]
        )
        users_by_email = self.users_repository.get_by_emails(
            [email for _, _, email in entries if email]
        )
        docente_role_ids = [
            role.id
            for role in self.users_repository.get_roles_by_names(
                [RoleName.DOCENTE.value]
            )
        ]

        results: list[dict] = []
        seen_codes: set[str] = set()
        seen_emails: set[str] = set()

        for row_number, code, email in entries:
            status, detail = self._import_teacher_email(
                code,
                email,
                department_id,
                users_by_code,
                users_by_email,
                docente_role_ids,
                seen_codes,
                seen_emails,
            )
            results.append(
                {
                    "row": row_number,
                    "institutional_code": code,
                    "email": email,
                    "status": status,
                    "detail": detail,
                }
            )

        self.users_repository.commit()

        summary = {
            "total": len(results),
            "created": sum(r["status"] == "created" for r in results),
            "updated": sum(r["status"] == "updated" for r in results),
            "unchanged": sum(r["status"] == "unchanged" for r in results),
            "already_active": sum(r["status"] == "already_active" for r in results),
            "other_department": sum(
                r["status"] == "other_department" for r in results
            ),
            "errors": sum(r["status"] == "error" for r in results),
        }

        await self.audit_service.log(
            action="IMPORT",
            entity_name="teachers",
            entity_id=department_id,
            actor_id=current_user.get("id"),
            description=(
                "Importación de correos de docentes. "
                f"Filas: {summary['total']}, "
                f"creados: {summary['created']}, "
                f"actualizados: {summary['updated']}, "
                f"sin cambios: {summary['unchanged']}, "
                f"ya con acceso: {summary['already_active']}, "
                f"de otro departamento: {summary['other_department']}, "
                f"errores: {summary['errors']}"
            ),
        )

        return {"summary": summary, "rows": results}

    def _import_teacher_email(
        self,
        code: str,
        email: str,
        department_id: int,
        users_by_code: dict,
        users_by_email: dict,
        docente_role_ids: list[int],
        seen_codes: set[str],
        seen_emails: set[str],
    ) -> tuple[str, str]:
        """Apply one row of the email import (without committing) and return
        its ``(status, detail)``. Keeps the lookup maps and seen sets current
        so later rows see what earlier ones did."""

        if not code or not email:
            return "error", "Faltan el código o el correo"

        if not code.isdigit():
            return "error", "El código debe ser numérico"

        if email.count("@") != 1 or not email.endswith(INSTITUTIONAL_EMAIL_DOMAIN):
            return "error", f"El correo debe ser del dominio {INSTITUTIONAL_EMAIL_DOMAIN}"

        # "45" and "00045" are the same code (see api.utils.institutional_codes).
        key = code_key(code)

        if key in seen_codes:
            return "error", "El código está repetido en el archivo"

        if email in seen_emails:
            return "error", "El correo está repetido en el archivo"

        seen_codes.add(key)
        seen_emails.add(email)

        user = users_by_code.get(key)
        email_owner = users_by_email.get(email)

        if email_owner is not None and (user is None or email_owner.id != user.id):
            return (
                "error",
                "El correo ya pertenece a otro usuario "
                f"(código {email_owner.institutional_code or 'sin código'})",
            )

        if user is None:
            new_user, _ = self.users_repository.find_or_create_user(
                {
                    "uid": None,
                    "email": email,
                    "name": code,
                    "institutional_code": code,
                    "active": True,
                }
            )
            self.users_repository.replace_user_roles(new_user.id, docente_role_ids)
            self.users_repository.create_teacher(
                user_id=new_user.id, department_id=department_id, active=True
            )
            users_by_code[key] = new_user
            users_by_email[email] = new_user

            return (
                "created",
                "Docente registrado. Su nombre se completará al subir su evaluación.",
            )

        teacher = user.teacher

        if teacher is None:
            return "error", "El código pertenece a un usuario que no es docente"

        if teacher.department_id is not None and teacher.department_id != department_id:
            return "other_department", "El docente pertenece a otro departamento"

        # A teacher with no department (older imports left them unassigned)
        # belongs to the department that claims them.
        claimed = ""
        if teacher.department_id is None:
            self.users_repository.set_teacher_department(teacher, department_id)
            claimed = " Se asignó a tu departamento."

        if user.uid:
            if user.email.lower() == email:
                return "already_active", "Ya inicia sesión con este correo." + claimed

            return (
                "already_active",
                f"Ya inició sesión con {user.email}; se respetó su correo." + claimed,
            )

        if user.email.lower() == email:
            return "unchanged", "Ya tenía este correo." + claimed

        previous_email = user.email
        self.users_repository.assign_fields(user, {"email": email})
        users_by_email[email] = user

        return "updated", f"Correo actualizado: {previous_email} → {email}." + claimed

    @staticmethod
    def _normalize_header(cell) -> str:
        """A header cell lowercased, trimmed and without accents ("Código" → "codigo")."""

        text = unicodedata.normalize("NFKD", str(cell or "").strip().lower())

        return "".join(ch for ch in text if not unicodedata.combining(ch))

    @staticmethod
    def _cell_text(row: tuple, index: int) -> str:
        """A cell as trimmed text. Excel stores a numeric code as a float
        (1152185.0), so whole numbers lose the trailing ``.0``."""

        value = row[index] if index < len(row) else None

        if value is None:
            return ""

        if isinstance(value, float) and value.is_integer():
            value = int(value)

        return str(value).strip()

    def _enrich_teacher_to_dict(self, teacher, roles: list[str] | None = None) -> dict:
        """Convert TeacherModel to dict with user data attached if available.

        Pass `roles` when the caller already bulk-fetched them for a list of
        teachers (see `get_all`/`get_all_with_averages`); otherwise this fetches
        them with a single-user query, fine for the single-teacher call sites
        (`get_by_id`, `create`, `create_with_user`, `update`, `delete`)."""

        data = teacher_to_dict(teacher)

        if teacher.user_id and teacher.user:
            if roles is None:
                roles = self.users_repository.get_user_role_names(teacher.user.id)
            data["user"] = user_to_dict(teacher.user, roles=roles)

        return data

    @staticmethod
    def _parse_excel(file_bytes: bytes) -> list[tuple]:
        """Parse Excel file and return rows as list of tuples."""

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
        ws = wb.active

        if not ws:
            raise ValidationError("El archivo Excel está vacío o no tiene hojas")

        return list(ws.iter_rows(values_only=True))

    @staticmethod
    def _parse_csv(file_bytes: bytes) -> list[tuple]:
        """Parse CSV file and return rows as list of tuples."""

        text = file_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        return [tuple(row) for row in reader]
