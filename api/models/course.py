"""
Course model
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class CourseModel(Base):
    """
    Course model
    """

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

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
