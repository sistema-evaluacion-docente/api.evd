"""
Teachers controller
"""

import io

import openpyxl
from fastapi.param_functions import Depends

from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.teachers import TeachersRepository, get_teachers_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.teacher import TeacherCreate, TeacherUpdate
from api.schemas.user import UserCreate


class TeachersController:
    """Teachers controller"""

    def __init__(
        self,
        repository: TeachersRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
        academic_periods_repository: AcademicPeriodsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository
        self.academic_periods_repository = academic_periods_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        if isinstance(current_user, dict):
            return current_user.get("id")

        user = await self.users_repository.get_by_uid(current_user.uid)

        return user["id"] if user else None

    async def _enrich_teacher(self, teacher: dict) -> dict:
        """Attach user data to a teacher dict if user_id exists."""

        if teacher.get("user_id"):
            users = await self.users_repository.get_by_ids([teacher["user_id"]])

            if users:
                teacher["user"] = users[0]

        return teacher

    async def _enrich_teachers(self, teachers: list[dict]) -> list[dict]:
        """Attach user data to a list of teacher dicts."""

        user_ids = [t["user_id"] for t in teachers if t.get("user_id")]

        if not user_ids:
            return teachers

        users = await self.users_repository.get_by_ids(user_ids)
        users_map = {u["id"]: u for u in users}

        for teacher in teachers:
            if teacher.get("user_id") and teacher["user_id"] in users_map:
                teacher["user"] = users_map[teacher["user_id"]]

        return teachers

    async def create(self, data: TeacherCreate, current_user) -> dict:
        """Create a new teacher, rejecting duplicate institutional codes."""

        existing = await self.repository.get_by_institutional_code(
            data.institutional_code
        )

        if existing:
            raise ValueError(
                f"A teacher with institutional code '{data.institutional_code}' already exists"
            )

        teacher = await self.repository.create(data)
        teacher = await self._enrich_teacher(teacher)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="teachers",
                operation="CREATE",
                element=f"Teacher {teacher.get('id')}",
                description=f"Se creó el profesor con código {data.institutional_code}, departamento {data.department_id}, tipo contrato: {data.contract_type}, activo: {data.active}",
                created_at=None,
            )
        )

        return teacher

    async def upload_excel(
        self, file_bytes: bytes, department_id: int, current_user
    ) -> dict:
        """Parse an Excel file and bulk-create teachers for the given department."""

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
        ws = wb.active

        if not ws:
            raise ValueError("El archivo Excel está vacío o no tiene hojas")

        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            raise ValueError(
                "El archivo Excel debe contener al menos un encabezado y una fila de datos"
            )

        header = [str(c).strip().lower() if c else "" for c in rows[0]]
        expected = {"nombre", "email", "codigo", "contrato"}
        actual = set(header)

        if not expected.issubset(actual):
            missing = expected - actual

            raise ValueError(
                f"Faltan columnas requeridas en el Excel: {', '.join(sorted(missing))}"
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

        existing_teachers = await self.repository.get_by_institutional_codes(codes)
        existing_codes = {t["institutional_code"] for t in existing_teachers}

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

            existing_user = await self.users_repository.get_by_email(row["email"])
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
                    username=row["email"].split("@")[0],
                    name=row["nombre"],
                    department_id=department_id,
                    active=True,
                    institutional_code=row["codigo_institucional"],
                    contract_type=row["tipo_contrato"],
                )

                user = await self.users_repository.save(user_data)

                created.append(user)
                existing_codes.add(row["codigo_institucional"])

            except ValueError as e:
                skipped.append(
                    {
                        "fila": row,
                        "razon": str(e),
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "fila": row,
                        "razon": f"Error inesperado: {str(e)}",
                    }
                )

        total_count = len(data_rows)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="teachers",
                operation="BULK_CREATE",
                element=f"Departamento {department_id}",
                description=(
                    f"Importación masiva de docentes. "
                    f"Total filas: {total_count}, "
                    f"Creados: {len(created)}, "
                    f"Omitidos: {len(skipped)}, "
                    f"Errores: {len(errors)}"
                ),
                created_at=None,
            )
        )

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        """Get all teachers with pagination and search."""

        teachers, total = await self.repository.get_all(
            page=page, limit=limit, search=search
        )

        return await self._enrich_teachers(teachers), total

    async def get_history(self, teacher_id: int) -> dict | None:
        """Get teacher's historical averages across all periods."""

        return await self.repository.get_history(teacher_id)

    async def get_by_id(self, teacher_id: int) -> dict | None:
        """Get a teacher by ID."""

        teacher = await self.repository.get_by_id(teacher_id)
        if not teacher:
            return None
        return await self._enrich_teacher(teacher)

    async def delete(self, teacher_id: int, current_user) -> dict | None:
        """Delete a teacher by ID."""

        teacher = await self.repository.get_by_id(teacher_id)

        if not teacher:
            return None

        deleted = await self.repository.delete(teacher_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="teachers",
                operation="DELETE",
                element=f"Teacher {teacher_id}",
                description=f"Se eliminó el profesor con código {teacher.get('institutional_code')}",
                created_at=None,
            )
        )

        return deleted

    async def count_by_department(
        self, department_id: int, academic_period_id: int
    ) -> dict:
        """Count teachers in a specific department for current and previous period."""

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

        return await self.repository.count_by_department(
            department_id, academic_period_id, previous_period_id
        )

    async def update(
        self, teacher_id: int, data: TeacherUpdate, current_user
    ) -> dict | None:
        """Update a teacher's fields."""

        teacher = await self.repository.get_by_id(teacher_id)

        if not teacher:
            return None

        updated = await self.repository.update(teacher_id, data)
        updated = await self._enrich_teacher(updated)

        changes = []
        for field in (
            "institutional_code",
            "department_id",
            "contract_type",
            "user_id",
            "active",
        ):
            new_val = getattr(data, field, None)
            if new_val is not None and new_val != teacher.get(field):
                old_val = teacher.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")
        desc = "Se actualizó el profesor #" + str(teacher_id)
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"
        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="teachers",
                operation="UPDATE",
                element=f"Teacher {teacher_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated


def get_teachers_controller(
    repository: TeachersRepository = Depends(get_teachers_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
):
    """Get teachers controller"""

    return TeachersController(
        repository, audits_repository, users_repository, academic_periods_repository
    )
