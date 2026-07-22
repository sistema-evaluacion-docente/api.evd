"""
Teacher model
"""

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class TeacherModel(Base):
    """
    Teacher model
    """

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    contract_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=True
    )
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)

    user: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", back_populates="teacher", uselist=False
    )

    academic_groups: Mapped[list["AcademicGroupModel"]] = relationship(
        "AcademicGroupModel", back_populates="teacher"
    )

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
