"""
Audit repository
"""

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
        )

        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)

        return audit_to_dict(audit)

    async def get_all(self, page: int = 1, limit: int = 10):
        """
        Get paginated audit logs
        """

        offset = (page - 1) * limit
        query = self.db.query(AuditModel)
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
