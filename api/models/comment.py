"""
Comment model
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class CommentModel(Base):
    """
    Comment model — qualitative student comments extracted from the PDF
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=True)
    academic_groups_id = Column(Integer, ForeignKey("academic_groups.id"), nullable=True)
    original_text = Column(Text, nullable=True)
    risk_level = Column(Integer, ForeignKey("risk_levels.id"), nullable=True)
    pedagogical_category_id = Column(
        Integer, ForeignKey("pedagogical_categories.id"), nullable=True
    )

    risk_level_rel = relationship("RiskLevelModel", lazy="joined", foreign_keys=[risk_level])
    pedagogical_category_rel = relationship(
        "PedagogicalCategoryModel", lazy="joined", foreign_keys=[pedagogical_category_id]
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
