"""Repository for audit-related database operations."""

from datetime import timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.audit import AuditModel
from api.repositories.base import BaseRepository
from api.schemas.audit import AuditFilters
from api.utils.get_audit import get_audit


class AuditsRepository(BaseRepository[AuditModel]):
    """Repository for audit-related database operations."""

    def __init__(self, db: Session):
        super().__init__(AuditModel, db)

    def search(
        self,
        filters: AuditFilters,
        pagination: PaginationParams,
    ) -> tuple[list[AuditModel], int]:
        """Search for audits based on filters and pagination parameters."""

        query = self.db.query(AuditModel).options(joinedload(AuditModel.user))

        if filters.actor_id is not None:
            query = query.filter(AuditModel.user_id == filters.actor_id)

        if filters.entity_name is not None:
            query = query.filter(AuditModel.table_name == filters.entity_name)

        if filters.operation is not None:
            query = query.filter(AuditModel.operation == filters.operation)

        if filters.date_from is not None and filters.date_to is not None:
            bogota_tz = ZoneInfo("America/Bogota")

            date_from_start = filters.date_from.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_to_start = filters.date_to.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            if date_from_start == date_to_start:
                date_from_bogota = date_from_start.replace(tzinfo=bogota_tz)
                next_day_bogota = date_from_bogota + timedelta(days=1)
                date_from_utc = date_from_bogota.astimezone(ZoneInfo("UTC"))
                next_day_utc = next_day_bogota.astimezone(ZoneInfo("UTC"))

                query = query.filter(
                    AuditModel.created_at >= date_from_utc,
                    AuditModel.created_at < next_day_utc,
                )
            else:
                date_from_bogota = date_from_start.replace(tzinfo=bogota_tz)
                date_to_bogota = date_to_start.replace(tzinfo=bogota_tz)
                date_from_utc = date_from_bogota.astimezone(ZoneInfo("UTC"))
                date_to_end_bogota = date_to_bogota + timedelta(days=1)
                date_to_utc = date_to_end_bogota.astimezone(ZoneInfo("UTC"))

                query = query.filter(
                    AuditModel.created_at >= date_from_utc,
                    AuditModel.created_at < date_to_utc,
                )
        elif filters.date_from is not None:
            bogota_tz = ZoneInfo("America/Bogota")
            date_from_start = filters.date_from.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_from_bogota = date_from_start.replace(tzinfo=bogota_tz)
            date_from_utc = date_from_bogota.astimezone(ZoneInfo("UTC"))
            query = query.filter(AuditModel.created_at >= date_from_utc)
        elif filters.date_to is not None:
            bogota_tz = ZoneInfo("America/Bogota")
            date_to_start = filters.date_to.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_to_end_bogota = date_to_start.replace(tzinfo=bogota_tz) + timedelta(
                days=1
            )
            date_to_utc = date_to_end_bogota.astimezone(ZoneInfo("UTC"))
            query = query.filter(AuditModel.created_at < date_to_utc)

        if filters.search is not None:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        AuditModel.element.ilike(like_term),
                        AuditModel.description.ilike(like_term),
                        AuditModel.table_name.ilike(like_term),
                    )
                )

        query = query.order_by(AuditModel.created_at.desc())

        return self.paginate(query, pagination)

    def get_by_id_with_element_data(self, audit_id: int) -> dict | None:
        """Get an audit by ID with element_data resolved."""

        audit = (
            self.db.query(AuditModel)
            .options(joinedload(AuditModel.user))
            .filter(AuditModel.id == audit_id)
            .first()
        )

        if not audit:
            return None

        # element_data = get_audit(str(audit.element), self.db) if audit.element else None

        return {
            "id": audit.id,
            "user_id": audit.user_id,
            "user": audit.user,
            "table_name": audit.table_name,
            "operation": audit.operation,
            "element": audit.element,
            "description": audit.description,
            "element_data": None,  # element_data,
            "created_at": audit.created_at,
            "updated_at": audit.updated_at,
        }

    def create_audit(self, data) -> AuditModel:
        """Create a new audit log."""

        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()

        return self.create(data)


def get_audits_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for AuditsRepository."""

    return AuditsRepository(db)
