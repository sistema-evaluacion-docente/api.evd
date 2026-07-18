"""Dependency injection for department-related operations."""

from fastapi import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.services.department_service import DepartmentService


def get_department_service(
    departments_repository: DepartmentsRepository = Depends(get_departments_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
) -> DepartmentService:
    """Dependency injection for DepartmentService."""

    return DepartmentService(
        departments_repository,
        users_repository,
        audits_repository,
    )
