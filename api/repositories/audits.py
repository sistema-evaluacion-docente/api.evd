"""
Audit repository
"""

from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.audit import AuditModel
from api.schemas.audit import AuditCreate, AuditUpdate
from api.serializers.audits import audit_to_dict
from api.utils.get_audit import get_audit


class AuditsRepository:
    """
    Class audit repository
    """

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: AuditCreate):
        """
        Create an audit log
        """

        audit = AuditModel(
            user_id=data.user_id,
            table_name=data.table_name,
            operation=data.operation,
            element=data.element,
            description=data.description,
        )

        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)

        return audit_to_dict(audit)

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        table_name: str | None = None,
        operation: str | None = None,
        search: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        """
        Get paginated audit logs
        """

        offset = (page - 1) * limit
        query = self.db.query(AuditModel)

        if table_name:
            query = query.filter(AuditModel.table_name == table_name)
        if operation:
            query = query.filter(AuditModel.operation == operation)
        if search:
            query = query.filter(
                or_(
                    AuditModel.element.ilike(f"%{search}%"),
                    AuditModel.description.ilike(f"%{search}%"),
                )
            )
        if start_date:
            start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            query = query.filter(AuditModel.created_at >= start_datetime)
        if end_date:
            end_datetime = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
            query = query.filter(AuditModel.created_at <= end_datetime)

        total = query.count()

        audits = query.order_by(AuditModel.id.desc()).offset(offset).limit(limit).all()

        return {
            "items": [audit_to_dict(audit) for audit in audits],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def get_by_id(self, audit_id: int):
        """
        Get audit log by id
        """

        audit = self.db.query(AuditModel).filter(AuditModel.id == audit_id).first()

        if not audit:
            return None

        element_data = await get_audit(str(audit.element), self.db)

        result = audit_to_dict(audit)
        result = {**result, "element_data": element_data}

        return result

    async def update(self, audit_id: int, data: AuditUpdate):
        """
        Update audit log by id
        """

        audit = self.db.query(AuditModel).filter(AuditModel.id == audit_id).first()

        if not audit:
            return None

        for field, value in data.model_dump().items():
            if value is not None:
                setattr(audit, field, value)

        self.db.commit()
        self.db.refresh(audit)

        return audit_to_dict(audit)

    async def delete(self, audit_id: int):
        """
        Delete audit log by id
        """

        audit = self.db.query(AuditModel).filter(AuditModel.id == audit_id).first()

        if not audit:
            return None

        audit_dict = audit_to_dict(audit)
        self.db.delete(audit)
        self.db.commit()

        return audit_dict


def get_audits_repository(db: Annotated[Session, Depends(get_db)]):
    """
    Get audits repository
    """

    return AuditsRepository(db)
