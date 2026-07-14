"""
Improvement plan evidence model — a PDF the teacher (or the director) attaches
to a plan as proof of compliance, optionally tied to a specific item.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanEvidenceModel(Base):
    """
    Improvement plan evidence model.

    ``item_id`` is optional: an evidence can support the plan as a whole or a
    single commitment. If the item is removed the evidence survives detached.
    """

    __tablename__ = "improvement_plan_evidences"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="evidences"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
