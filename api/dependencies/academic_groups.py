"""Dependency injection for academic group-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.academic_groups import (
    AcademicGroupsRepository,
    get_academic_groups_repository,
)
from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.services.academic_group_service import AcademicGroupService
from api.services.audit_service import AuditService


def get_academic_group_service(
    academic_groups_repository: AcademicGroupsRepository = Depends(
        get_academic_groups_repository
    ),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> AcademicGroupService:
    """Dependency injection for AcademicGroupService."""

    return AcademicGroupService(
        academic_groups_repository,
        academic_periods_repository,
        audit_service,
    )
