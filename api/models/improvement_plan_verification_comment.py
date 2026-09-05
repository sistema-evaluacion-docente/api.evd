"""
Improvement plan verification comment model — a student comment that brings
back the same complaint the plan was meant to settle.
"""

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanVerificationCommentModel(Base):
    """
    A comment of the verification period matching the pedagogical category of a
    qualitative commitment of the plan.

    A comment is never a verdict against a target — there is no number to
    compare — so this is reported as *reincidencia*, with the comments listed
    for the director to read and judge.

    ``is_alert`` separates the two risk levels that are kept: ALTO raises the
    alert, because that is the level the whole system already treats as worth
    acting on (see ``api/utils/plan_suggestion.py``); MEDIO is stored as context
    only, so the signal is not lost without inflating false positives.
    """

    __tablename__ = "improvement_plan_verification_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_verifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The qualitative commitment this comment echoes. Null when the plan item
    # cited comments the AI never categorised, and the match fell back to "any
    # high-risk comment of the period".
    item_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Indexed for the cascade, not for a query: deleting an evaluation bulk
    # deletes all its comments, and every one of them makes Postgres look for
    # the rows pointing here. Without an index that is a full scan per comment.
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pedagogical_category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("pedagogical_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Snapshots, so the finding keeps reading the same if the catalogue changes.
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    risk_level_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    verification: Mapped["ImprovementPlanVerificationModel"] = relationship(  # noqa: F821
        "ImprovementPlanVerificationModel", back_populates="comment_findings"
    )
    # What the student actually wrote stays on the comment itself; this row
    # only records that it came back and how it was classified.
    comment: Mapped["CommentModel"] = relationship(  # noqa: F821
        "CommentModel", lazy="joined", foreign_keys=[comment_id]
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
