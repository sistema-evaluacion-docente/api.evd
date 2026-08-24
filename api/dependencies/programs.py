"""Dependency injection for programs."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.programs import ProgramsRepository, get_programs_repository
from api.services.audit_service import AuditService
from api.services.program_service import ProgramService


def get_program_service(
    programs_repository: ProgramsRepository = Depends(get_programs_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> ProgramService:
    """Get program service instance."""

    return ProgramService(
        programs_repository=programs_repository,
        audit_service=audit_service,
    )
