"""
Improvement plan verification model — what the *following* semester says about
a plan that is already closed.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanVerificationModel(Base):
    """
    Verification of an improvement plan against its verification period.

    A plan is closed when the Formato 3 is signed, which happens **before** the
    grades that would prove the teacher improved even exist. This row is the
    after-the-fact answer: it is written when the evaluation of the verification
    period is uploaded, and it never touches the closing the director signed.

    It is filled in two passes, because the two inputs are ready at different
    moments: the scores as soon as the evaluation finishes processing, the
    comment findings only once the AI has classified them.
    """

    __tablename__ = "improvement_plan_verifications"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "period_id", name="uq_plan_verification_plan_period"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_periods.id"), nullable=False, index=True
    )
    # The evaluation that fed the last pass — traceability only.
    evaluation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True
    )
    # Verdict of the numeric pass: MEJORO / NO_MEJORO / SIN_DATOS.
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SIN_DATOS"
    )
    scores_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comments_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Stamped when the director has already been told, so re-running a pass
    # never notifies twice for the same finding.
    scores_notified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comments_notified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    plan: Mapped["ImprovementPlanModel"] = relationship(  # noqa: F821
        "ImprovementPlanModel", back_populates="verifications"
    )
    items: Mapped[list["ImprovementPlanVerificationItemModel"]] = relationship(  # noqa: F821
        "ImprovementPlanVerificationItemModel",
        back_populates="verification",
        cascade="all, delete-orphan",
    )
    comment_findings: Mapped[list["ImprovementPlanVerificationCommentModel"]] = (  # noqa: F821
        relationship(
            "ImprovementPlanVerificationCommentModel",
            back_populates="verification",
            cascade="all, delete-orphan",
        )
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
