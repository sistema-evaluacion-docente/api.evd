"""
Setting model
"""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class SettingModel(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False, default="NUMBER")
    description = Column(Text, nullable=True)
    changed_by = Column(String(50), nullable=True)

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
