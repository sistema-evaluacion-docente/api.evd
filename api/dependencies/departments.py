"""Dependency injection for department-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.departments import (
    DepartmentsRepository,
    get_departments_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.services.audit_service import AuditService
from api.services.department_service import DepartmentService


def get_department_service(
    departments_repository: DepartmentsRepository = Depends(get_departments_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> DepartmentService:
    """Dependency injection for DepartmentService."""

    return DepartmentService(
        departments_repository,
        users_repository,
        audit_service,
    )
