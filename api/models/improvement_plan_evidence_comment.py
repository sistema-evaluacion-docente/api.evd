"""
Improvement plan evidence comment model — the message thread between director and
teacher about a requested deliverable.
"""

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanEvidenceCommentModel(Base):
    """
    Improvement plan evidence comment model — one message on a request thread.

    ``is_system`` marks the entries the API writes itself (e.g. when an evidence
    is rejected) so the UI can render them differently from human messages.
    """

    __tablename__ = "improvement_plan_evidence_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_evidence_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    request: Mapped["ImprovementPlanEvidenceRequestModel"] = relationship(
        "ImprovementPlanEvidenceRequestModel", back_populates="comments"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
