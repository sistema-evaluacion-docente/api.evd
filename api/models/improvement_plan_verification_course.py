"""
Improvement plan verification course model — the same indicator, per subject.
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


class ImprovementPlanVerificationCourseModel(Base):
    """
    One subject the teacher taught in the verification period, with their
    average for the indicator being verified.

    These are the groups of the **new** period, not the ones printed on the
    plan: an academic group belongs to a single period, so the ones frozen in
    ``improvement_plan_courses`` cannot be measured again. That also covers the
    case that matters most — the same shortcoming reappearing in a different
    subject.

    Course name and group are snapshots, so the finding keeps reading the same
    if the group is later edited.
    """

    __tablename__ = "improvement_plan_verification_courses"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    verification_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_verification_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("academic_groups.id", ondelete="SET NULL"), nullable=True
    )
    course_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    course_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result_value: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    met: Mapped[bool] = mapped_column(Boolean, nullable=False)

    item: Mapped["ImprovementPlanVerificationItemModel"] = relationship(  # noqa: F821
        "ImprovementPlanVerificationItemModel", back_populates="courses"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
