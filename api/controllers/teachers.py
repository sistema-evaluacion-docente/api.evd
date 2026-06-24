"""
Teachers controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.teachers import TeachersRepository, get_teachers_repository
from api.schemas.audit import AuditCreate
from api.schemas.teacher import TeacherCreate, TeacherUpdate


class TeachersController:
    """Teachers controller"""

    def __init__(
        self,
        repository: TeachersRepository,
        audits_repository: AuditsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository

    async def create(self, data: TeacherCreate, current_user) -> dict:
        """Create a new teacher, rejecting duplicate institutional codes."""

        existing = await self.repository.get_by_institutional_code(data.institutional_code)

        if existing:
            raise ValueError(
                f"A teacher with institutional code '{data.institutional_code}' already exists"
            )

        teacher = await self.repository.create(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="teachers",
                operation="create",
                element=f"Teacher {teacher.get('id')}",
                description=f"Se creó el profesor con código {data.institutional_code}, departamento {data.department_id}, tipo contrato: {data.contract_type}, activo: {data.active}",
                created_at=None,
            )
        )

        return teacher

    async def get_all(self) -> list[dict]:
        """Get all teachers."""

        return await self.repository.get_all()

    async def get_by_id(self, teacher_id: int) -> dict | None:
        """Get a teacher by ID."""

        return await self.repository.get_by_id(teacher_id)

    async def update(
        self, teacher_id: int, data: TeacherUpdate, current_user
    ) -> dict | None:
        """Update a teacher's fields."""

        teacher = await self.repository.get_by_id(teacher_id)

        if not teacher:
            return None

        updated = await self.repository.update(teacher_id, data)

        changes = []
        for field in ("institutional_code", "department_id", "contract_type", "user_id", "active"):
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
                user_id=current_user.uid,
                table_name="teachers",
                operation="update",
                element=f"Teacher {teacher_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated


def get_teachers_controller(
    repository: TeachersRepository = Depends(get_teachers_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
):
    """Get teachers controller"""

    return TeachersController(repository, audits_repository)
