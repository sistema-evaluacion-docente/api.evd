"""
Improvement plan checkpoint model — the three formal follow-up stages of a plan
during the semester: inicio, mitad y semana 16.
"""

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanCheckpointModel(Base):
    """
    Improvement plan checkpoint model.

    ``stage`` is one of INICIO / MITAD / SEMANA_16.
    ``status`` is PENDIENTE / COMPLETADO.
    """

    __tablename__ = "improvement_plan_checkpoints"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_date: Mapped[Optional[datetime.date]] = mapped_column(
        Date, nullable=True
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDIENTE"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="checkpoints"
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
