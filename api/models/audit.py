"""
Audit model
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.user import UserModel


class AuditModel(Base):
    """
    Audit model for system logs
    """

    __tablename__ = "audit"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    table_name = Column(String(255), nullable=True)
    operation = Column(String(255), nullable=True)
    element = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    user = relationship(UserModel, backref="audits")

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        onupdate=func.now(),
    )
