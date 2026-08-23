"""
Setting model
"""

import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class SettingModel(Base):
    """A configuration value, either institutional or owned by a department.

    ``department_id`` is what separates the two scopes: NULL is the
    institutional value that an ADMIN maintains, and a department id is the
    value that department's director maintains for itself. A department value
    overrides the institutional one for that department; when it is missing,
    the institutional value applies.
    """

    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("key", "department_id", name="uq_settings_key_department"),
        Index(
            "uq_settings_key_global",
            "key",
            unique=True,
            postgresql_where=text("department_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NUMBER"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    changed_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    department: Mapped[Optional["DepartmentModel"]] = relationship(
        "DepartmentModel",
        uselist=False,
        viewonly=True,
    )

    changed_by_user: Mapped[Optional["UserModel"]] = relationship(
        "UserModel",
        primaryjoin="UserModel.uid == foreign(SettingModel.changed_by)",
        viewonly=True,
        uselist=False,
    )

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
