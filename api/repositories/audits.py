"""
Audit repository
"""

from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.audit import AuditModel
from api.schemas.audit import AuditCreate, AuditUpdate
from api.serializers.audits import audit_to_dict


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
            created_at=data.created_at or date.today(),
        )

        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)

        return audit_to_dict(audit)

    async def get_all(self):
        """
        Get all audit logs
        """

        audits = self.db.query(AuditModel).order_by(AuditModel.id.desc()).all()
        return [audit_to_dict(audit) for audit in audits]

    async def get_by_id(self, audit_id: int):
        """
        Get audit log by id
        """

        audit = self.db.query(AuditModel).filter(AuditModel.id == audit_id).first()

        if not audit:
            return None

        return audit_to_dict(audit)

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
