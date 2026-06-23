"""
Setting history model
"""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class SettingHistoryModel(Base):
    __tablename__ = "settings_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    changed_by = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=True)

    changed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
