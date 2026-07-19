"""Service for department-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.repositories.departments import DepartmentsRepository
from api.repositories.users import UsersRepository
from api.schemas.department import (
    DepartmentCreate,
    DepartmentFilters,
    DepartmentUpdate,
    DirectorSummary,
)
from api.schemas.pagination import build_paginated_response
from api.serializers.departments import department_to_dict
from api.services.audit_service import AuditService


class DepartmentService:
    """Service for department-related business operations."""

    def __init__(
        self,
        departments_repository: DepartmentsRepository,
        users_repository: UsersRepository,
        audit_service: AuditService,
    ):
        self.departments_repository = departments_repository
        self.users_repository = users_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: DepartmentFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all departments based on filters and pagination."""

        departments, total = self.departments_repository.search(filters, pagination)

        department_ids = [d.id for d in departments]
        directors_by_dept = self.departments_repository.get_directors_by_department_ids(
            department_ids
        )
        teacher_counts = self.departments_repository.count_teachers_by_department_ids(
            department_ids
        )

        items = []
        for dept in departments:
            data = department_to_dict(dept)
            director_info = directors_by_dept.get(dept.id)
            data["director"] = (
                DirectorSummary(**director_info) if director_info else None
            )
            data["teacher_count"] = teacher_counts.get(dept.id, 0)
            items.append(data)

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, department_id: int) -> dict | None:
        """Retrieve a department by ID."""

        department = self.departments_repository.get_by_id(department_id)

        if not department:
            return None

        data = department_to_dict(department)
        director_info = self.departments_repository.get_director_by_department_id(
            department_id
        )
        data["director"] = DirectorSummary(**director_info) if director_info else None

        teacher_count = self.departments_repository.count_teachers_by_department_ids(
            [department_id]
        )
        data["teacher_count"] = teacher_count.get(department_id, 0)

        return data

    async def create(self, data: DepartmentCreate, current_user: dict) -> dict:
        """Create a new department, rejecting duplicate codes."""

        existing = self.departments_repository.get_by_code(data.code)

        if existing:
            raise ResourceAlreadyExistsError("department", "code", data.code)

        department = self.departments_repository.create(data.model_dump())
        self.departments_repository.db.commit()
        self.departments_repository.db.refresh(department)

        result = department_to_dict(department)
        result["director"] = None
        result["teacher_count"] = 0

        await self.audit_service.log(
            action="CREATE",
            entity_name="departments",
            entity_id=department.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el departamento {data.name} "
                f"(código: {data.code}, facultad ID: {data.faculty_id})"
            ),
        )

        return result

    async def update(
        self, department_id: int, data: DepartmentUpdate, current_user: dict
    ) -> dict | None:
        """Update a department's fields."""

        department = self.departments_repository.get_by_id(department_id)

        if not department:
            return None

        old_data = department_to_dict(department)
        payload = data.model_dump(exclude_unset=True)

        updated = self.departments_repository.update_department(department, payload)
        result = department_to_dict(updated)

        director_info = self.departments_repository.get_director_by_department_id(
            department_id
        )
        result["director"] = DirectorSummary(**director_info) if director_info else None

        teacher_count = self.departments_repository.count_teachers_by_department_ids(
            [department_id]
        )
        result["teacher_count"] = teacher_count.get(department_id, 0)

        changes = []
        for field in ("code", "name", "faculty_id", "active"):
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = "Se actualizó el departamento"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="departments",
            entity_id=department_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return result

    async def delete(self, department_id: int, current_user: dict) -> dict | None:
        """Delete a department, rejecting if it has active teachers or director."""

        department = self.departments_repository.get_by_id(department_id)

        if not department:
            return None

        if self.departments_repository.has_active_teachers(department_id):
            raise ValidationError(
                "No se puede eliminar el departamento porque tiene profesores activos asignados"
            )

        if self.departments_repository.has_active_director(department_id):
            raise ValidationError(
                "No se puede eliminar el departamento porque tiene un director activo asignado"
            )

        old_data = department_to_dict(department)
        self.departments_repository.delete_department(department_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="departments",
            entity_id=department_id,
            actor_id=current_user.get("id"),
            description=f"Se eliminó el departamento {old_data.get('name')} (código: {old_data.get('code')})",
        )

        return old_data
