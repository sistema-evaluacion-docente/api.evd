"""
Faculty model
"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class FacultyModel(Base):
    """
    Faculty model
    """

    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(255), unique=True, nullable=False)
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
