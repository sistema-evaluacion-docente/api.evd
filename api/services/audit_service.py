"""Service for audit-related business operations."""

from api.core.pagination import PaginationParams
from api.repositories.audits import AuditsRepository
from api.schemas.audit import AuditFilters
from api.schemas.pagination import build_paginated_response
from api.serializers.audits import audit_to_dict


class AuditService:
    """Service for audit-related business operations."""

    def __init__(self, audits_repository: AuditsRepository):
        self.audits_repository = audits_repository

    async def list_audits(
        self,
        filters: AuditFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all audits based on filters and pagination."""

        audits, total = self.audits_repository.search(filters, pagination)
        items = [audit_to_dict(audit) for audit in audits]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, audit_id: int) -> dict | None:
        """Retrieve an audit by ID with element_data resolved."""

        return self.audits_repository.get_by_id_with_element_data(audit_id)

    async def log(
        self,
        action: str,
        entity_name: str,
        entity_id: int | str,
        actor_id: int | None,
        description: str | None = None,
    ) -> None:
        """Log an audit action. Called by other services to record operations."""

        self.audits_repository.create_audit(
            {
                "user_id": actor_id,
                "table_name": entity_name,
                "operation": action,
                "element": f"{entity_name} {entity_id}",
                "description": description,
            }
        )
        self.audits_repository.db.commit()
