"""Service for Director entity."""

from api.core.pagination import PaginationParams
from api.exceptions import (
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.repositories.audits import AuditsRepository
from api.repositories.departments import DepartmentsRepository
from api.repositories.directors import DirectorsRepository
from api.repositories.users import UsersRepository
from api.schemas.audit import AuditCreate
from api.schemas.director import (
    DirectorCreate,
    DirectorFilters,
    DirectorUpdate,
    UserSummary,
    DepartmentSummary,
)
from api.schemas.user import RoleName, UserCreate
from api.services.user_service import UserService
from api.serializers.directors import director_to_dict


class DirectorService:
    """Service para operaciones de Director."""

    def __init__(
        self,
        directors_repository: DirectorsRepository,
        users_repository: UsersRepository,
        departments_repository: DepartmentsRepository,
        audits_repository: AuditsRepository,
        user_service: UserService,
    ):
        self.directors_repository = directors_repository
        self.users_repository = users_repository
        self.departments_repository = departments_repository
        self.audits_repository = audits_repository
        self.user_service = user_service

    async def get_all(
        self, filters: DirectorFilters, pagination: PaginationParams
    ) -> dict:
        """Obtener todos los directores con filtros y paginación."""
        directors, total = self.directors_repository.search(filters, pagination)

        items = []
        for director in directors:
            director_dict = director_to_dict(director)

            # Enriquecer con datos de usuario
            user = self.users_repository.get(director.user_id)
            if user:
                director_dict["user"] = UserSummary(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    avatar_url=user.avatar_url,
                )

            # Enriquecer con datos de departamento
            department = self.departments_repository.get(director.department_id)
            if department:
                director_dict["department"] = DepartmentSummary(
                    id=department.id,
                    name=department.name,
                    code=department.code,
                )

            items.append(director_dict)

        return {
            "items": items,
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "pages": (total + pagination.limit - 1) // pagination.limit,
        }

    async def get_by_id(self, director_id: int) -> dict | None:
        """Obtener director por ID."""
        director = self.directors_repository.get(director_id)
        if not director:
            return None

        director_dict = director_to_dict(director)

        # Enriquecer con datos de usuario
        user = self.users_repository.get(director.user_id)
        if user:
            director_dict["user"] = UserSummary(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
            )

        # Enriquecer con datos de departamento
        department = self.departments_repository.get(director.department_id)
        if department:
            director_dict["department"] = DepartmentSummary(
                id=department.id,
                name=department.name,
                code=department.code,
            )

        return director_dict

    async def create(self, data: DirectorCreate, current_user: dict) -> dict:
        """Create a new director and associated user."""

        department = self.departments_repository.get(data.department_id)

        if not department:
            raise ResourceNotFoundError("Department", data.department_id)

        existing_user = self.users_repository.get_by_email(data.email)

        if existing_user:
            raise ResourceAlreadyExistsError("User", "email", data.email)

        existing_director = self.directors_repository.get_by_department_id(
            data.department_id
        )

        if existing_director:
            raise ValidationError("Este departamento ya tiene un director asignado")

        user_data = UserCreate(
            email=data.email,
            name=data.name,
            username=data.username,
            uid=data.uid,
            avatar_url=data.avatar_url,
            institutional_code=data.institutional_code,
            contract_type=data.contract_type,
            roles=[RoleName.DIRECTOR_DE_DEPARTAMENTO],
        )

        user = await self.user_service.create_user_with_roles(user_data)

        director = self.directors_repository.create(
            {
                "user_id": user["id"],
                "department_id": data.department_id,
            }
        )

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user["id"],
                table_name="directors",
                operation="CREATE",
                element=f"Director {director.id}",
                description=f"Se creó el director para el departamento {department.name}",
            )
        )

        return await self.get_by_id(director.id)

    async def update(
        self, director_id: int, data: DirectorUpdate, current_user: dict
    ) -> dict | None:
        """Update a director."""

        director = self.directors_repository.get(director_id)
        if not director:
            return None

        if (
            data.department_id is not None
            and data.department_id != director.department_id
        ):
            existing_director = self.directors_repository.get_by_department_id(
                data.department_id
            )

            if existing_director:
                raise ResourceAlreadyExistsError(
                    "Director", "department_id", str(data.department_id)
                )

        if data.user_id is not None and data.user_id != director.user_id:
            existing_user_director = self.directors_repository.get_by_user_id(
                data.user_id
            )

            if existing_user_director and existing_user_director.department_id != (
                data.department_id or director.department_id
            ):
                raise ValueError("Este usuario ya es director de otro departamento")

        director = self.directors_repository.update_director(director, data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user["id"],
                table_name="directors",
                operation="UPDATE",
                element=f"Director {director_id}",
                description=f"Se actualizó el director {director_id}",
            )
        )

        return await self.get_by_id(director.id)

    async def delete(self, director_id: int, current_user: dict) -> dict | None:
        """Delete a director."""

        director = self.directors_repository.get(director_id)

        if not director:
            return None

        director_dict = director_to_dict(director)
        self.directors_repository.delete_director(director)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user["id"],
                table_name="directors",
                operation="DELETE",
                element=f"Director {director_id}",
                description=f"Se eliminó el director {director_id}",
            )
        )

        return director_dict

    async def assign_director(
        self, department_id: int, user_id: int, current_user: dict
    ) -> dict:
        """Asign a user as director of a department, replacing any existing director."""

        department = self.departments_repository.get(department_id)

        if not department:
            raise ResourceNotFoundError("Department", department_id)

        user = self.users_repository.get(user_id)

        if not user:
            raise ResourceNotFoundError("User", user_id)

        director = self.directors_repository.assign_director(user_id, department_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user["id"],
                table_name="directors",
                operation="ASSIGN",
                element=f"Director {director.id}",
                description=f"Se asignó el usuario {user_id} como director del departamento {department.name}",
            )
        )

        return await self.get_by_id(director.id)
