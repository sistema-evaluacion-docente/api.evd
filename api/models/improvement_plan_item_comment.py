"""
Improvement plan item comment model — join between a plan item and the student
comments the director cited to justify it.
"""

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanItemCommentModel(Base):
    """
    Improvement plan item comment model.

    Mainly used by aspect 5 ("Observaciones de los Estudiantes"), where the form
    asks for the negative situation described by the student, but any item may
    quote comments as supporting evidence.
    """

    __tablename__ = "improvement_plan_item_comments"
    __table_args__ = (
        UniqueConstraint("item_id", "comment_id", name="uq_plan_item_comment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item: Mapped["ImprovementPlanItemModel"] = relationship(
        "ImprovementPlanItemModel", back_populates="comment_links"
    )
    comment: Mapped["CommentModel"] = relationship("CommentModel", lazy="joined")

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
