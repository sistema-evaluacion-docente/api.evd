"""Dependency injection for user-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.users import UsersRepository, get_users_repository
from api.services.audit_service import AuditService
from api.services.user_service import UserService


def get_user_service(
    users_repository: UsersRepository = Depends(get_users_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> UserService:
    """Dependency injection for UserService."""

    return UserService(users_repository, audit_service)
