"""
Setting model
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class SettingModel(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NUMBER"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    effective_from: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
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
