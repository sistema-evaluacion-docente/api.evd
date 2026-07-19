"""Dependency injection for Directors."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.dependencies.users import get_user_service
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.repositories.directors import DirectorsRepository, get_directors_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.services.audit_service import AuditService
from api.services.director_service import DirectorService
from api.services.user_service import UserService


def get_director_service(
    directors_repository: DirectorsRepository = Depends(get_directors_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    departments_repository: DepartmentsRepository = Depends(get_departments_repository),
    audit_service: AuditService = Depends(get_audit_service),
    user_service: UserService = Depends(get_user_service),
) -> DirectorService:
    """Dependency para obtener DirectorService."""

    return DirectorService(
        directors_repository=directors_repository,
        users_repository=users_repository,
        departments_repository=departments_repository,
        audit_service=audit_service,
        user_service=user_service,
    )
