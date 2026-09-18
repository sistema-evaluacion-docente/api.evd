"""Dependency injection for faculties."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.dependencies.users import get_user_service
from api.repositories.faculties import FacultiesRepository, get_faculties_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.services.audit_service import AuditService
from api.services.faculty_service import FacultyService
from api.services.user_service import UserService


def get_faculty_service(
    faculties_repository: FacultiesRepository = Depends(get_faculties_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    audit_service: AuditService = Depends(get_audit_service),
    user_service: UserService = Depends(get_user_service),
) -> FacultyService:
    """Get faculty service instance."""

    return FacultyService(
        faculties_repository=faculties_repository,
        users_repository=users_repository,
        audit_service=audit_service,
        user_service=user_service,
    )
