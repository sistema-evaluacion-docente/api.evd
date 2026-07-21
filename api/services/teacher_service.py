"""Service for teacher-related business operations."""

import csv
import io

import openpyxl

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.teachers import TeachersRepository
from api.repositories.users import UsersRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)
from api.schemas.user import UserCreate
from api.serializers.teachers import teacher_to_dict
from api.serializers.users import user_to_dict
from api.services.audit_service import AuditService
from api.services.user_service import UserService


class TeacherService:
    """Service for teacher-related business operations."""

    def __init__(
        self,
        teachers_repository: TeachersRepository,
        users_repository: UsersRepository,
        audit_service: AuditService,
        academic_periods_repository: AcademicPeriodsRepository,
        user_service: UserService,
    ):
        self.teachers_repository = teachers_repository
        self.users_repository = users_repository
        self.audit_service = audit_service
        self.academic_periods_repository = academic_periods_repository
        self.user_service = user_service

    async def get_all(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all teachers based on filters and pagination."""

        teachers, total = self.teachers_repository.search(filters, pagination)
        items = [self._enrich_teacher_to_dict(t) for t in teachers]

        return build_paginated_response(items, total, pagination)

    async def get_all_with_averages(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
        academic_period_id: int,
    ) -> dict:
        """Retrieve teachers with overall_average for a given academic period."""

        teachers, total = self.teachers_repository.search(filters, pagination)
        teacher_ids = [t.id for t in teachers]

        avgs = self.teachers_repository.get_teacher_averages_by_period(
            teacher_ids, academic_period_id
        )

        items = []
        for t in teachers:
            d = self._enrich_teacher_to_dict(t)
            d["overall_average"] = avgs.get(t.id)
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

        teacher = self.teachers_repository.create(data.model_dump())
        self.teachers_repository.db.commit()
        self.teachers_repository.db.refresh(teacher)

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
        payload = data.model_dump(exclude_unset=True)

        updated = self.teachers_repository.update_teacher(teacher, payload)
        result = self._enrich_teacher_to_dict(updated)

        changes = []
        for field in (
            "institutional_code",
            "department_id",
            "contract_type",
            "user_id",
            "active",
        ):
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

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

    async def get_history(self, teacher_id: int) -> dict | None:
        """Get teacher's historical averages across all periods."""

        return self.teachers_repository.get_history(teacher_id)

    async def upload_excel(
        self, file_bytes: bytes, filename: str, department_id: int, current_user: dict
    ) -> dict:
        """Parse an Excel or CSV file and bulk-create teachers for the given department."""

        is_csv = filename.lower().endswith(".csv")

        if is_csv:
            rows = self._parse_csv(file_bytes)
        else:
            rows = self._parse_excel(file_bytes)

        if len(rows) < 2:
            file_type = "CSV" if is_csv else "Excel"
            raise ValueError(
                f"El archivo {file_type} debe contener al menos un encabezado y una fila de datos"
            )

        header = [str(c).strip().lower() if c else "" for c in rows[0]]
        expected = {"nombre", "email", "codigo", "contrato"}
        actual = set(header)

        if not expected.issubset(actual):
            missing = expected - actual
            raise ValueError(
                f"Faltan columnas requeridas en el archivo: {', '.join(sorted(missing))}"
            )

        col_idx = {name: i for i, name in enumerate(header)}

        data_rows = []
        for row in rows[1:]:
            if not any(row):
                continue

            nombre = (
                str(row[col_idx["nombre"]]).strip() if row[col_idx["nombre"]] else ""
            )
            email = str(row[col_idx["email"]]).strip() if row[col_idx["email"]] else ""
            codigo = (
                str(row[col_idx["codigo"]]).strip() if row[col_idx["codigo"]] else ""
            )
            contrato = (
                str(row[col_idx["contrato"]]).strip()
                if row[col_idx["contrato"]]
                else ""
            )

            data_rows.append(
                {
                    "nombre": nombre,
                    "email": email,
                    "codigo_institucional": codigo,
                    "tipo_contrato": contrato or None,
                }
            )

        codes = [
            r["codigo_institucional"] for r in data_rows if r["codigo_institucional"]
        ]

        existing_teachers = self.teachers_repository.get_by_institutional_codes(codes)
        existing_codes = {t.institutional_code for t in existing_teachers}

        created = []
        skipped = []
        errors = []

        for row in data_rows:
            if not row["nombre"] or not row["email"] or not row["codigo_institucional"]:
                errors.append(
                    {
                        "fila": row,
                        "razon": "Faltan campos obligatorios (nombre, email, codigo institucional)",
                    }
                )
                continue

            if row["codigo_institucional"] in existing_codes:
                skipped.append(
                    {
                        "fila": row,
                        "razon": f"El código institucional '{row['codigo_institucional']}' ya existe",
                    }
                )
                continue

            existing_user = self.users_repository.get_by_email(row["email"])
            if existing_user:
                skipped.append(
                    {
                        "fila": row,
                        "razon": f"El email '{row['email']}' ya está registrado",
                    }
                )
                continue

            try:
                user_data = UserCreate(
                    email=row["email"],
                    name=row["nombre"],
                    active=True,
                    institutional_code=row["codigo_institucional"],
                    contract_type=row["tipo_contrato"],
                )

                await self.user_service.create_user_with_roles(user_data)

                created.append(
                    {
                        "nombre": row["nombre"],
                        "email": row["email"],
                        "codigo_institucional": row["codigo_institucional"],
                        "tipo_contrato": row["tipo_contrato"],
                    }
                )

                existing_codes.add(row["codigo_institucional"])

            except ValueError as e:
                skipped.append({"fila": row, "razon": str(e)})
            except Exception as e:
                errors.append({"fila": row, "razon": f"Error inesperado: {str(e)}"})

        await self.audit_service.log(
            action="BULK_CREATE",
            entity_name="teachers",
            entity_id=department_id,
            actor_id=current_user.get("id"),
            description=(
                f"Importación masiva de docentes. "
                f"Total filas: {len(data_rows)}, "
                f"Creados: {len(created)}, "
                f"Omitidos: {len(skipped)}, "
                f"Errores: {len(errors)}"
            ),
        )

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }

    def _enrich_teacher_to_dict(self, teacher) -> dict:
        """Convert TeacherModel to dict with user data attached if available."""

        data = teacher_to_dict(teacher)

        if teacher.user_id and teacher.user:
            roles = self.users_repository.get_user_role_names(teacher.user.id)
            data["user"] = user_to_dict(teacher.user, roles=roles)

        return data

    @staticmethod
    def _parse_excel(file_bytes: bytes) -> list[tuple]:
        """Parse Excel file and return rows as list of tuples."""

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
        ws = wb.active

        if not ws:
            raise ValueError("El archivo Excel está vacío o no tiene hojas")

        return list(ws.iter_rows(values_only=True))

    @staticmethod
    def _parse_csv(file_bytes: bytes) -> list[tuple]:
        """Parse CSV file and return rows as list of tuples."""

        text = file_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        return [tuple(row) for row in reader]
