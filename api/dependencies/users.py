"""Dependency injection for user-related operations."""

from fastapi import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.services.user_service import UserService


def get_user_service(
    users_repository: UsersRepository = Depends(get_users_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
) -> UserService:
    """Dependency injection for UserService."""

    return UserService(users_repository, audits_repository)
