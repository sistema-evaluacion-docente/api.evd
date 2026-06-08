"""
User model
"""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class UserModel(Base):
    """
    User model
    """

    __tablename__ = "users"

    uid = Column(Text, primary_key=True, index=True)  # firebase uid
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    active = Column(Boolean, nullable=True, default=True)
    avatar_url = Column(Text, nullable=True)

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
