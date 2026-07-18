"""
Dependency injection for faculties.
"""

from fastapi import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.faculties import FacultiesRepository, get_faculties_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.services.faculty_service import FacultyService


def get_faculty_service(
    faculties_repository: FacultiesRepository = Depends(get_faculties_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
) -> FacultyService:
    """Get faculty service instance."""

    return FacultyService(
        faculties_repository=faculties_repository,
        users_repository=users_repository,
        audits_repository=audits_repository,
    )
