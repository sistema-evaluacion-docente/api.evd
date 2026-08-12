"""
Comment model
"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class CommentModel(Base):
    """
    Comment model — qualitative student comments extracted from the PDF
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    evaluation_id = Column(
        Integer, ForeignKey("evaluations.id"), nullable=True, index=True
    )
    academic_groups_id = Column(
        Integer, ForeignKey("academic_groups.id"), nullable=True
    )
    original_text = Column(Text, nullable=True)
    risk_level = Column(
        Integer, ForeignKey("risk_levels.id"), nullable=True, index=True
    )
    risk_score = Column(Float, nullable=True)
    risk_level_modified_by_director = Column(Boolean, nullable=False, default=False)
    pedagogical_category_modified_by_director = Column(
        Boolean, nullable=False, default=False
    )

    risk_level_rel = relationship(
        "RiskLevelModel", lazy="joined", foreign_keys=[risk_level]
    )
    # 0..N pedagogical categories, each with its own confidence score.
    pedagogical_categories = relationship(
        "CommentPedagogicalCategoryModel",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
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
