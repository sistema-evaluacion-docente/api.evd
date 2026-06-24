"""
Departments controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.schemas.audit import AuditCreate
from api.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentsController:
    """Departments controller"""

    def __init__(
        self,
        repository: DepartmentsRepository,
        audits_repository: AuditsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository

    async def create(self, data: DepartmentCreate, current_user) -> dict:
        """Create a new department, rejecting duplicate codes."""
        existing = await self.repository.get_by_code(data.code)
        if existing:
            raise ValueError(
                f"A department with code '{data.code}' already exists"
            )
        department = await self.repository.create(data)
        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="departments",
                operation="create",
                element=f"Department {department.get('id')}",
                description=f"Se creó el departamento {data.name} (código: {data.code}, facultad: {data.faculty})",
                created_at=None,
            )
        )
        return department

    async def get_all(self) -> list[dict]:
        """Get all departments."""
        return await self.repository.get_all()

    async def get_by_id(self, department_id: int) -> dict | None:
        """Get a department by ID."""
        return await self.repository.get_by_id(department_id)

    async def update(
        self, department_id: int, data: DepartmentUpdate, current_user
    ) -> dict | None:
        """Update a department's fields."""
        department = await self.repository.get_by_id(department_id)
        if not department:
            return None
        updated = await self.repository.update(department_id, data)
        updated = await self.repository.update(department_id, data)
        changes = []
        for field in ("code", "name", "faculty", "active"):
            new_val = getattr(data, field, None)
            if new_val is not None and new_val != department.get(field):
                old_val = department.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")
        desc = "Se actualizó el departamento"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"
        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="departments",
                operation="update",
                element=f"Department {department_id}",
                description=desc,
                created_at=None,
            )
        )
        return updated


def get_departments_controller(
    repository: DepartmentsRepository = Depends(get_departments_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
):
    """Get departments controller"""
    return DepartmentsController(repository, audits_repository)
