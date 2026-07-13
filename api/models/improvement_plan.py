"""
Improvement plan model (Plan de Seguimiento Docente)
"""

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanModel(Base):
    """
    Improvement plan model — one plan per teacher, anchored to the period where
    the low performance was detected (origin) and the following period whose
    grades confirm compliance (verification).
    """

    __tablename__ = "improvement_plans"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teachers.id"), nullable=False, index=True
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    origin_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_periods.id"), nullable=False
    )
    verification_period_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("academic_periods.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # BORRADOR / EN_SEGUIMIENTO / RESULTADO_DISPONIBLE /
    # CERRADO_CUMPLIDO / CERRADO_NO_CUMPLIDO / CERRADO_MANUAL
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EN_SEGUIMIENTO"
    )
    close_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["ImprovementPlanItemModel"]] = relationship(
        "ImprovementPlanItemModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ImprovementPlanItemModel.order",
    )
    checkpoints: Mapped[list["ImprovementPlanCheckpointModel"]] = relationship(
        "ImprovementPlanCheckpointModel",
        back_populates="plan",
        cascade="all, delete-orphan",
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
