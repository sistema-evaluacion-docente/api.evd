"""
Evaluation score model
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class EvaluationScoreModel(Base):
    """
    Evaluation score model — one row per academic group within an evaluation
    """

    __tablename__ = "evaluation_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    academic_group_id = Column(Integer, ForeignKey("academic_groups.id"), nullable=False)
    respondent_count = Column(Integer, nullable=False)
    overall_average = Column(Numeric(4, 2), nullable=True)

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
