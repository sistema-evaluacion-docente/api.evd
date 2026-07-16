"""
Directors controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.repositories.directors import DirectorsRepository, get_directors_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.director import DirectorCreate, DirectorRecordCreate, DirectorUpdate
from api.schemas.user import UserCreate


class DirectorsController:
    """Directors controller"""

    def __init__(
        self,
        repository: DirectorsRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
        departments_repository: DepartmentsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository
        self.departments_repository = departments_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = await self.users_repository.get_by_uid(current_user.uid)

        return user["id"] if user else None

    async def create(self, data: DirectorCreate, current_user) -> dict:
        """Create a new director."""

        department = await self.departments_repository.get_by_id(data.department_id)

        if not department:
            raise ValueError(f"El departamento con id {
                             data.department_id} no existe")

        existing = await self.repository.get_by_department_id(data.department_id)

        if existing:
            raise ValueError(
                f"El departamento {data.department_id} ya tiene un director asignado (user_id: {
                    existing['user_id']})"
            )

        username = data.email.split("@")[0]

        user_data = UserCreate(
            email=data.email,
            username=username,
            name=data.name,
            active=True,
            institutional_code=data.institutional_code,
            contract_type=data.contract_type,
            roles=data.roles,
        )

        user = await self.users_repository.save(user_data)
        user_id = user["id"]

        director_record = DirectorRecordCreate(
            user_id=user_id,
            department_id=data.department_id,
        )

        director = await self.repository.create(director_record)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="directors",
                operation="CREATE",
                element=f"Director {director.get('id')}",
                description=f"Se creó el director: usuario {
                    user_id} para departamento {data.department_id}",
                created_at=None,
            )
        )

        return await self.repository.get_by_id(director["id"])

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all directors with pagination and optional search."""

        return await self.repository.get_all(search=search, page=page, limit=limit)

    async def get_by_id(self, director_id: int) -> dict | None:
        """Get a director by ID."""

        return await self.repository.get_by_id(director_id)

    async def update(
        self, director_id: int, data: DirectorUpdate, current_user
    ) -> dict | None:
        """Update a director."""

        director = await self.repository.get_by_id(director_id)

        if not director:
            return None

        if data.department_id is not None:
            department = await self.departments_repository.get_by_id(data.department_id)

            if not department:
                raise ValueError(f"El departamento con id {
                                 data.department_id} no existe")

            existing = await self.repository.get_by_department_id(data.department_id)

            if existing and existing["id"] != director_id:
                raise ValueError(
                    f"El departamento {data.department_id} ya tiene un director asignado (user_id: {
                        existing['user_id']})"
                )

        if data.user_id is not None:
            users = await self.users_repository.get_by_ids([data.user_id])

            if not users:
                raise ValueError(f"El usuario con id {data.user_id} no existe")

        updated = await self.repository.update(director_id, data)

        changes = []

        for field in ("user_id", "department_id", "active"):
            new_val = getattr(data, field, None)

            if new_val is not None and new_val != director.get(field):
                old_val = director.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = "Se actualizó el director"

        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="directors",
                operation="UPDATE",
                element=f"Director {director_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated

    async def delete(self, director_id: int, current_user) -> dict | None:
        """Delete a director."""

        director = await self.repository.get_by_id(director_id)

        if not director:
            return None

        deleted = await self.repository.delete(director_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="directors",
                operation="DELETE",
                element=f"Director {director_id}",
                description=f"Se eliminó el director: usuario {
                    director['user_id']} del departamento {director['department_id']}",
                created_at=None,
            )
        )

        return deleted

    async def assign_director(
        self, department_id: int, user_id: int, current_user
    ) -> dict:
        """Assign a director to a department."""

        department = await self.departments_repository.get_by_id(department_id)

        if not department:
            raise ValueError(f"El departamento con id {department_id} no existe")

        users = await self.users_repository.get_by_ids([user_id])

        if not users:
            raise ValueError(f"El usuario con id {user_id} no existe")

        director = await self.repository.assign_director(user_id, department_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="directors",
                operation="ASSIGN",
                element=f"Director {director.get('id')}",
                description=f"Se asignó el usuario {
                    user_id} como director del departamento {department.get('name')}",
                created_at=None,
            )
        )

        return director


def get_directors_controller(
    repository: DirectorsRepository = Depends(get_directors_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    departments_repository: DepartmentsRepository = Depends(get_departments_repository),
):
    """Get directors controller"""

    return DirectorsController(
        repository, audits_repository, users_repository, departments_repository
    )
