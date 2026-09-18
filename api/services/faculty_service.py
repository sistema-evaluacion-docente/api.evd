"""Faculty service module."""

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.repositories.faculties import FacultiesRepository
from api.repositories.users import UsersRepository
from api.schemas.faculty import DeanSummary, FacultyCreate, FacultyFilters, FacultyUpdate
from api.schemas.user import RoleName, UserUpdate
from api.serializers.deans import dean_to_dict
from api.serializers.faculties import faculty_to_dict
from api.services.audit_service import AuditService
from api.services.user_service import UserService


class FacultyService:
    """Service for Faculty operations."""

    def __init__(
        self,
        faculties_repository: FacultiesRepository,
        users_repository: UsersRepository,
        audit_service: AuditService,
        user_service: UserService,
    ):
        self.faculties_repository = faculties_repository
        self.users_repository = users_repository
        self.audit_service = audit_service
        self.user_service = user_service

    async def get_all(
        self, filters: FacultyFilters, pagination: PaginationParams
    ) -> dict:
        """Get all faculties with filters and pagination."""

        faculties, total = self.faculties_repository.search(filters, pagination)

        faculty_ids = [f.id for f in faculties]
        dept_counts = self.faculties_repository.get_department_counts(faculty_ids)
        deans_by_faculty = self.faculties_repository.get_deans_by_faculty_ids(
            faculty_ids
        )

        items = []
        for faculty in faculties:
            data = faculty_to_dict(faculty)
            data["department_count"] = dept_counts.get(faculty.id, 0)
            dean_info = deans_by_faculty.get(faculty.id)
            data["dean"] = DeanSummary(**dean_info) if dean_info else None
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
        dean_info = self.faculties_repository.get_dean_with_user_by_faculty_id(
            faculty_id
        )
        data["dean"] = DeanSummary(**dean_info) if dean_info else None
        return data

    async def create(self, data: FacultyCreate, current_user: dict) -> dict:
        """Create a new faculty."""

        existing = self.faculties_repository.get_by_code(data.code)
        if existing:
            raise ResourceAlreadyExistsError("Faculty", "code", data.code)

        faculty = self.faculties_repository.create_faculty(data)

        await self.audit_service.log(
            action="CREATE",
            entity_name="faculties",
            entity_id=faculty.id,
            actor_id=current_user.get("id"),
            description=f"Se creó la facultad {faculty.name} (código: {faculty.code})",
        )

        result = faculty_to_dict(faculty)
        result["department_count"] = 0
        result["dean"] = None
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

        await self.audit_service.log(
            action="UPDATE",
            entity_name="faculties",
            entity_id=faculty_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        result = faculty_to_dict(updated)
        dept_counts = self.faculties_repository.get_department_counts([faculty.id])
        result["department_count"] = dept_counts.get(faculty.id, 0)
        dean_info = self.faculties_repository.get_dean_with_user_by_faculty_id(
            faculty_id
        )
        result["dean"] = DeanSummary(**dean_info) if dean_info else None
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

        await self.audit_service.log(
            action="DELETE",
            entity_name="faculties",
            entity_id=faculty_id,
            actor_id=current_user.get("id"),
            description=f"Se eliminó la facultad {faculty_data['name']} (código: {faculty_data['code']})",
        )

        return faculty_data

    async def assign_dean(
        self, faculty_id: int, user_id: int, current_user: dict
    ) -> dict:
        """Assign a user as dean of a faculty, replacing any existing dean."""

        faculty = self.faculties_repository.get(faculty_id)

        if not faculty:
            raise ResourceNotFoundError("Faculty", faculty_id)

        user = self.users_repository.get(user_id)

        if not user:
            raise ResourceNotFoundError("User", user_id)

        current_roles = self.users_repository.get_user_role_names(user.id)

        if RoleName.DECANO.value not in current_roles:
            new_roles = current_roles + [RoleName.DECANO.value]
            await self.user_service.update_user(user.uid, UserUpdate(roles=new_roles))

        dean = self.faculties_repository.assign_dean(user_id, faculty_id)

        await self.audit_service.log(
            action="ASSIGN",
            entity_name="deans",
            entity_id=dean.id,
            actor_id=current_user["id"],
            description=f"Se asignó el usuario {user_id} como decano de la facultad {faculty.name}",
        )

        return dean_to_dict(dean)

    async def unassign_dean(
        self, faculty_id: int, current_user: dict
    ) -> dict | None:
        """Remove the dean assignment from a faculty.

        Deletes the `deans` row outright rather than deactivating it, same
        reasoning as DirectorService.unassign_director: an inactive row
        still pointing at a faculty would misleadingly read as "still dean,
        just inactive".
        """

        faculty = self.faculties_repository.get(faculty_id)

        if not faculty:
            raise ResourceNotFoundError("Faculty", faculty_id)

        dean = self.faculties_repository.get_dean_by_faculty_id(faculty_id)

        if not dean:
            return None

        dean_dict = dean_to_dict(dean)
        user_id = dean.user_id

        self.faculties_repository.delete_dean(dean)

        await self._retire_dean_role(user_id)

        await self.audit_service.log(
            action="UNASSIGN",
            entity_name="deans",
            entity_id=dean_dict["id"],
            actor_id=current_user["id"],
            description=f"Se desasignó el decano de la facultad {faculty.name}",
        )

        return dean_dict

    async def _retire_dean_role(self, user_id: int) -> None:
        """Drop `DECANO` from a user who just lost their `deans` row,
        keeping their other roles. Mirrors
        DirectorService._retire_director_role."""

        user = self.users_repository.get(user_id)

        if not user:
            return

        current_roles = self.users_repository.get_user_role_names(user.id)

        if RoleName.DECANO.value not in current_roles:
            return

        remaining_roles = [
            role for role in current_roles if role != RoleName.DECANO.value
        ]

        # A user needs at least one role (`UserUpdate.roles` rejects an empty
        # list); if this was their only one, leave it — unassigning a dean
        # doesn't mean to strip the user's last role and lock them out.
        if remaining_roles:
            await self.user_service.update_user(
                user.uid, UserUpdate(roles=remaining_roles)
            )
