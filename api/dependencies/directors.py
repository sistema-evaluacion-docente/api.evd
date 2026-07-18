"""Dependency injection for Directors."""

from fastapi import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.repositories.directors import DirectorsRepository, get_directors_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.services.director_service import DirectorService
from api.services.user_service import UserService
from api.dependencies.users import get_user_service


def get_director_service(
    directors_repository: DirectorsRepository = Depends(get_directors_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    departments_repository: DepartmentsRepository = Depends(get_departments_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    user_service: UserService = Depends(get_user_service),
) -> DirectorService:
    """Dependency para obtener DirectorService."""

    return DirectorService(
        directors_repository=directors_repository,
        users_repository=users_repository,
        departments_repository=departments_repository,
        audits_repository=audits_repository,
        user_service=user_service,
    )
