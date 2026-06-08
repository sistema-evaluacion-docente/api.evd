"""
Department model
"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class DepartmentModel(Base):
    """
    Department model
    """

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, nullable=False)
    code = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    faculty = Column(String(255), nullable=True)
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
