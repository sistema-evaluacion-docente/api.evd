"""Dependency injection for teacher-related operations."""

from fastapi import Depends

from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.teachers import TeachersRepository, get_teachers_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.dependencies.users import get_user_service
from api.services.teacher_service import TeacherService
from api.services.user_service import UserService


def get_teacher_service(
    teachers_repository: TeachersRepository = Depends(get_teachers_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
    user_service: UserService = Depends(get_user_service),
) -> TeacherService:
    """Dependency injection for TeacherService."""

    return TeacherService(
        teachers_repository,
        users_repository,
        audits_repository,
        academic_periods_repository,
        user_service,
    )
