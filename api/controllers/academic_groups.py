"""
Academic groups controller
"""

from fastapi.param_functions import Depends

from api.repositories.academic_groups import (
    AcademicGroupsRepository,
    get_academic_groups_repository,
)
from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.academic_group import AcademicGroupCreate, AcademicGroupUpdate
from api.schemas.audit import AuditCreate


class AcademicGroupsController:
    """Academic groups controller"""

    def __init__(
        self,
        repository: AcademicGroupsRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = await self.users_repository.get_by_uid(current_user.uid)
        return user["id"] if user else None

    async def create(self, data: AcademicGroupCreate, current_user) -> dict:
        """Create a new academic group, rejecting exact duplicates."""

        existing = await self.repository.get_by_course_teacher_period(
            data.course_id, data.teacher_id, data.academic_period_id
        )

        if existing:
            raise ValueError(
                "An academic group for this course, teacher and period already exists"
            )

        group = await self.repository.create(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_groups",
                operation="CREATE",
                element=f"AcademicGroup {group.get('id')}",
                description=f"Se creó el grupo académico {group.get('id')} para el curso {data.course_id}, profesor {data.teacher_id}, período {data.academic_period_id}, grupo: {data.group_name}",
                created_at=None,
            )
        )

        return group

    async def get_all(self) -> list[dict]:
        """Get all academic groups."""

        return await self.repository.get_all()

    async def get_by_id(self, group_id: int) -> dict | None:
        """Get an academic group by ID."""

        return await self.repository.get_by_id(group_id)

    async def update(
        self, group_id: int, data: AcademicGroupUpdate, current_user
    ) -> dict | None:
        """Update an academic group's fields."""

        group = await self.repository.get_by_id(group_id)

        if not group:
            return None

        updated = await self.repository.update(group_id, data)

        changes = []
        for field in ("course_id", "teacher_id", "academic_period_id", "group_name"):
            new_val = getattr(data, field, None)
            if new_val is not None and new_val != group.get(field):
                old_val = group.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")
        desc = "Se actualizó el grupo académico #" + str(group_id)
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"
        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="academic_groups",
                operation="UPDATE",
                element=f"AcademicGroup {group_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated


def get_academic_groups_controller(
    repository: AcademicGroupsRepository = Depends(get_academic_groups_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
):
    """Get academic groups controller"""

    return AcademicGroupsController(repository, audits_repository, users_repository)
