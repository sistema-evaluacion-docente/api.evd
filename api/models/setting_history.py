"""
Setting history model
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class SettingHistoryModel(Base):
    __tablename__ = "settings_history"
    __table_args__ = (
        Index("ix_settings_history_key_department", "key", "department_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
    )
    changed_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    changed_by_user: Mapped[Optional["UserModel"]] = relationship(
        "UserModel",
        primaryjoin="UserModel.uid == foreign(SettingHistoryModel.changed_by)",
        viewonly=True,
        uselist=False,
    )

    changed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
