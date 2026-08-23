"""
Improvement plan verification item model — one agreed target, measured again.
"""

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanVerificationItemModel(Base):
    """
    How one measurable commitment of the plan fared in the verification period.

    ``result_value`` is the teacher's average for the indicator across **all**
    their groups of that period: that is the figure the acta agreed on, and the
    one that decides ``met``. The per-course breakdown hangs off this row as
    context — a teacher can clear the target overall and still be under it in a
    single subject, which is worth telling the director about but is not what
    was signed.

    The target is copied here instead of read from the item, because the plan
    item keeps being the live record and this has to stay the photograph of what
    was compared.
    """

    __tablename__ = "improvement_plan_verification_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    verification_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_verifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # DIMENSION / QUESTION / OVERALL_AVERAGE, plus the dimension name or the
    # question code — same vocabulary as improvement_plan_items.
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # What had to be reached: the item's own target, or the institutional
    # threshold when the item did not set one.
    target_value: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    # Null when the verification period has no grades for this indicator.
    result_value: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    met: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    verification: Mapped["ImprovementPlanVerificationModel"] = relationship(  # noqa: F821
        "ImprovementPlanVerificationModel", back_populates="items"
    )
    courses: Mapped[list["ImprovementPlanVerificationCourseModel"]] = relationship(  # noqa: F821
        "ImprovementPlanVerificationCourseModel",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
