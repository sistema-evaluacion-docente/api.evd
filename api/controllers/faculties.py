"""
Faculties controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.faculties import (
    FacultiesRepository,
    get_faculties_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.faculty import FacultyCreate, FacultyUpdate


class FacultiesController:
    """Faculties controller"""

    def __init__(
        self,
        repository: FacultiesRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = await self.users_repository.get_by_uid(current_user.uid)
        return user["id"] if user else None

    async def create(self, data: FacultyCreate, current_user) -> dict:
        """Create a new faculty, rejecting duplicate codes."""
        existing = await self.repository.get_by_code(data.code)
        if existing:
            raise ValueError(f"A faculty with code '{data.code}' already exists")
        faculty = await self.repository.create(data)
        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="faculties",
                operation="CREATE",
                element=f"Faculty {faculty.get('id')}",
                description=f"Se creó la facultad {data.name} (código: {data.code})",
                created_at=None,
            )
        )
        return faculty

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all faculties with pagination and optional search."""
        return await self.repository.get_all(search=search, page=page, limit=limit)

    async def get_by_id(self, faculty_id: int) -> dict | None:
        """Get a faculty by ID."""
        return await self.repository.get_by_id(faculty_id)

    async def update(
        self, faculty_id: int, data: FacultyUpdate, current_user
    ) -> dict | None:
        """Update a faculty's fields."""
        faculty = await self.repository.get_by_id(faculty_id)

        if not faculty:
            return None

        updated = await self.repository.update(faculty_id, data)

        changes = []

        for field in ("name", "code", "active"):
            new_val = getattr(data, field, None)

            if new_val is not None and new_val != faculty.get(field):
                old_val = faculty.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = "Se actualizó la facultad"

        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="faculties",
                operation="UPDATE",
                element=f"Faculty {faculty_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated


def get_faculties_controller(
    repository: FacultiesRepository = Depends(get_faculties_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
):
    """Get faculties controller"""
    return FacultiesController(repository, audits_repository, users_repository)
