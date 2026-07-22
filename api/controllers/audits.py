"""Controller for audit-related operations."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.audits import get_audit_service
from api.schemas.audit import AuditFilters
from api.services.audit_service import AuditService


class AuditsController:
    """Controller for audit-related operations."""

    def __init__(self, service: AuditService):
        self.service = service

    async def get_all(
        self,
        filters: AuditFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all audits based on filters and pagination."""

        return await self.service.list_audits(filters, pagination)

    async def get_by_id(self, audit_id: int):
        """Retrieve an audit by ID."""

        return await self.service.get_by_id(audit_id)


def get_audits_controller(
    service: AuditService = Depends(get_audit_service),
):
    """Dependency injection for AuditsController."""

    return AuditsController(service)
