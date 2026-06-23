"""
Evaluation model
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class EvaluationModel(Base):
    """
    Evaluation model — one row per uploaded PDF (one per department per period)
    """

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Text, ForeignKey("users.uid"), nullable=True)
    academic_period_id = Column(Integer, ForeignKey("academic_periods.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    pdf_url = Column(String(255), nullable=True)
    status = Column(String(255), nullable=True)
    count = Column(Integer, nullable=True)

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
