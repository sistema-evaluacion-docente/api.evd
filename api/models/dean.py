"""
Dean model
"""

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class DeanModel(Base):
    """
    Dean model
    """

    __tablename__ = "deans"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    faculty_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("faculties.id"), nullable=False, unique=True, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["UserModel"] = relationship("UserModel", uselist=False)

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
