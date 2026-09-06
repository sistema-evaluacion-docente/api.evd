"""
Improvement plan document model — the generated and physically-signed PDFs of the
three official UFPS forms attached to a plan.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanDocumentModel(Base):
    """
    Improvement plan document model — one row per (plan, format).

    The system renders the form filled with the plan data into
    ``generated_pdf_url``; the director downloads it, collects the handwritten
    signatures and uploads the scan back into ``signed_pdf_url``. For
    ``FORMATO_1`` the "signed" slot holds the report received from the program.
    """

    __tablename__ = "improvement_plan_documents"
    __table_args__ = (
        UniqueConstraint("plan_id", "format_type", name="uq_plan_document_format"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # FORMATO_1 / FORMATO_2 / FORMATO_3
    format_type: Mapped[str] = mapped_column(String(20), nullable=False)

    generated_pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    signed_pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Name the file had on the director's machine. Stored apart from the path
    # because the path is a uuid: the UI shows this one back to him.
    signed_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="documents"
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
