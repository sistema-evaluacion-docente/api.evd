"""Dependency injection for evaluation-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.directors import (
    DirectorsRepository,
    get_directors_repository,
)
from api.repositories.evaluations import (
    EvaluationsRepository,
    get_evaluations_repository,
)
from api.repositories.users import UsersRepository, get_users_repository
from api.services.audit_service import AuditService
from api.services.evaluation_service import EvaluationService


def get_evaluation_service(
    evaluations_repository: EvaluationsRepository = Depends(get_evaluations_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
    directors_repository: DirectorsRepository = Depends(get_directors_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> EvaluationService:
    """Dependency injection for EvaluationService."""

    return EvaluationService(
        evaluations_repository,
        users_repository,
        academic_periods_repository,
        directors_repository,
        audit_service,
    )
