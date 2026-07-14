"""
Improvement plan item model — a single commitment/action within a plan,
optionally mapped to the indicator (dimension / pedagogical category /
overall average) where the teacher scored low.
"""

import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanItemModel(Base):
    """
    Improvement plan item model.

    ``target_type`` drives how compliance is verified against the verification
    period: DIMENSION / QUESTION / PEDAGOGICAL_CATEGORY / OVERALL_AVERAGE /
    QUALITATIVE. ``target_ref`` holds the dimension name, the question code
    (e.g. "011") or the pedagogical_category id (null for OVERALL_AVERAGE and
    QUALITATIVE).
    """

    __tablename__ = "improvement_plan_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="QUALITATIVE"
    )
    target_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    baseline_value: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    target_value: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    result_value: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    # PENDIENTE / EN_PROGRESO / CUMPLIDO / NO_CUMPLIDO
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDIENTE"
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="items"
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
