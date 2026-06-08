"""
Role model
"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class RoleModel(Base):
    """
    Role model
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=True, default=True)

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
