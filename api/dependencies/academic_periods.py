"""Dependency injection for academic period-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.evaluations import (
    EvaluationsRepository,
    get_evaluations_repository,
)
from api.services.academic_period_service import AcademicPeriodService
from api.services.audit_service import AuditService


def get_academic_period_service(
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
    evaluations_repository: EvaluationsRepository = Depends(get_evaluations_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> AcademicPeriodService:
    """Dependency injection for AcademicPeriodService."""

    return AcademicPeriodService(
        academic_periods_repository,
        evaluations_repository,
        audit_service,
    )
