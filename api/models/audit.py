"""
Audit model
"""

from datetime import date

from sqlalchemy import Column, Date, Integer, String

from api.database import Base


class AuditModel(Base):
    """
    Audit model for system logs
    """

    __tablename__ = "audit"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), nullable=True)
    table_name = Column(String(255), nullable=True)
    operation = Column(String(255), nullable=True)
    created_at = Column(Date, default=date.today)
