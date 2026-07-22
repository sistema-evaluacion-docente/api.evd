"""
User model
"""

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class UserModel(Base):
    """
    User model
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    uid: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, index=True
    )  # firebase uid
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    institutional_code: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    teacher: Mapped[Optional["TeacherModel"]] = relationship(
        "TeacherModel", back_populates="user", uselist=False
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
