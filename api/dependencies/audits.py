"""Dependency injection for audit-related operations."""

from fastapi import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.services.audit_service import AuditService


def get_audit_service(
    audits_repository: AuditsRepository = Depends(get_audits_repository),
) -> AuditService:
    """Dependency injection for AuditService."""

    return AuditService(audits_repository)
