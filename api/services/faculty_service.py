"""
Faculty service module.
"""

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ValidationError,
)
from api.repositories.audits import AuditsRepository
from api.repositories.faculties import FacultiesRepository
from api.repositories.users import UsersRepository
from api.schemas.audit import AuditCreate
from api.schemas.faculty import FacultyCreate, FacultyFilters, FacultyUpdate
from api.serializers.faculties import faculty_to_dict


class FacultyService:
    """Service for Faculty operations."""

    def __init__(
        self,
        faculties_repository: FacultiesRepository,
        users_repository: UsersRepository,
        audits_repository: AuditsRepository,
    ):
        self.faculties_repository = faculties_repository
        self.users_repository = users_repository
        self.audits_repository = audits_repository

    async def get_all(
        self, filters: FacultyFilters, pagination: PaginationParams
    ) -> dict:
        """Get all faculties with filters and pagination."""

        faculties, total = self.faculties_repository.search(filters, pagination)

        faculty_ids = [f.id for f in faculties]
        dept_counts = self.faculties_repository.get_department_counts(faculty_ids)

        items = []
        for faculty in faculties:
            data = faculty_to_dict(faculty)
            data["department_count"] = dept_counts.get(faculty.id, 0)
            items.append(data)

        return {
            "items": items,
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "pages": (total + pagination.limit - 1) // pagination.limit,
        }

    async def get_by_id(self, faculty_id: int) -> dict | None:
        """Get a faculty by ID."""

        faculty = self.faculties_repository.get(faculty_id)
        if not faculty:
            return None

        data = faculty_to_dict(faculty)
        dept_counts = self.faculties_repository.get_department_counts([faculty.id])
        data["department_count"] = dept_counts.get(faculty.id, 0)
        return data

    async def create(self, data: FacultyCreate, current_user: dict) -> dict:
        """Create a new faculty."""

        existing = self.faculties_repository.get_by_code(data.code)
        if existing:
            raise ResourceAlreadyExistsError("Faculty", "code", data.code)

        faculty = self.faculties_repository.create_faculty(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.get("id"),
                table_name="faculties",
                operation="CREATE",
                element=f"Faculty {faculty.id}",
                description=f"Se creó la facultad {faculty.name} (código: {faculty.code})",
            )
        )

        result = faculty_to_dict(faculty)
        result["department_count"] = 0
        return result

    async def update(
        self, faculty_id: int, data: FacultyUpdate, current_user: dict
    ) -> dict | None:
        """Update a faculty."""

        faculty = self.faculties_repository.get(faculty_id)
        if not faculty:
            return None

        if data.code is not None and data.code != faculty.code:
            existing = self.faculties_repository.get_by_code(data.code)
            if existing:
                raise ResourceAlreadyExistsError("Faculty", "code", data.code)

        old_name = faculty.name
        old_code = faculty.code

        updated = self.faculties_repository.update_faculty(faculty, data)

        changes = []
        if data.name is not None and data.name != old_name:
            changes.append(f"name cambió de {old_name} a {data.name}")
        if data.code is not None and data.code != old_code:
            changes.append(f"code cambió de {old_code} a {data.code}")
        if data.active is not None and data.active != faculty.active:
            changes.append(f"active cambió de {faculty.active} a {data.active}")

        desc = "Se actualizó la facultad"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.get("id"),
                table_name="faculties",
                operation="UPDATE",
                element=f"Faculty {faculty_id}",
                description=desc,
            )
        )

        result = faculty_to_dict(updated)
        dept_counts = self.faculties_repository.get_department_counts([faculty.id])
        result["department_count"] = dept_counts.get(faculty.id, 0)
        return result

    async def delete(self, faculty_id: int, current_user: dict) -> dict | None:
        """Delete a faculty."""

        faculty = self.faculties_repository.get(faculty_id)
        if not faculty:
            return None

        if self.faculties_repository.has_departments(faculty_id):
            raise ValidationError(
                "No se puede eliminar la facultad porque tiene departamentos asociados"
            )

        faculty_data = faculty_to_dict(faculty)
        self.faculties_repository.delete_faculty(faculty)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.get("id"),
                table_name="faculties",
                operation="DELETE",
                element=f"Faculty {faculty_id}",
                description=f"Se eliminó la facultad {faculty_data['name']} (código: {faculty_data['code']})",
            )
        )

        return faculty_data
