"""
Improvement plan checkpoint note model — one follow-up cell of the Formato 3
matrix: what the director recorded for a given aspect on a given seguimiento.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanCheckpointNoteModel(Base):
    """
    Improvement plan checkpoint note model.

    ``aspect`` is 1-5 (see ``api/utils/dimensions.py`` ASPECTS). The five rows are
    created empty alongside the checkpoint so the form always renders complete.
    """

    __tablename__ = "improvement_plan_checkpoint_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plan_checkpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aspect: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    checkpoint: Mapped["ImprovementPlanCheckpointModel"] = relationship(
        "ImprovementPlanCheckpointModel", back_populates="aspect_notes"
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
