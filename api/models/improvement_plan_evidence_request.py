"""
Improvement plan evidence request model — a specific deliverable the director
asks the teacher for (attendance lists, screenshots, ...).
"""

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanEvidenceRequestModel(Base):
    """
    Improvement plan evidence request model.

    ``status`` walks PENDIENTE -> EN_REVISION (teacher submitted) -> APROBADA /
    RECHAZADA. A rejection sends it back to PENDIENTE so the teacher can submit
    again; the conversation lives in ``comments``.
    """

    __tablename__ = "improvement_plan_evidence_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
        index=True,
    )
    requested_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # PENDIENTE / EN_REVISION / APROBADA / RECHAZADA
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDIENTE"
    )
    due_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    plan: Mapped["ImprovementPlanModel"] = relationship("ImprovementPlanModel")
    comments: Mapped[list["ImprovementPlanEvidenceCommentModel"]] = relationship(
        "ImprovementPlanEvidenceCommentModel",
        back_populates="request",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ImprovementPlanEvidenceCommentModel.created_at",
    )
    evidences: Mapped[list["ImprovementPlanEvidenceModel"]] = relationship(
        "ImprovementPlanEvidenceModel",
        back_populates="request",
        order_by="ImprovementPlanEvidenceModel.created_at",
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
