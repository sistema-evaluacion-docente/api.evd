"""
Evaluation model
"""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class EvaluationModel(Base):
    """
    Evaluation model — one row per department per period, backed by the one or
    two PDFs the university publishes for it (presencial and a distancia)
    """

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    academic_period_id = Column(
        Integer, ForeignKey("academic_periods.id"), nullable=True, index=True
    )
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    # One path, or several separated by commas — see api/utils/evaluation_pdfs.py.
    pdf_url = Column(Text, nullable=True)

    academic_period = relationship("AcademicPeriodModel", lazy="joined")
    active = Column(Boolean, nullable=True, default=True)
    status = Column(String(255), nullable=True)
    ai_status = Column(String(255), nullable=True, default="PENDING")
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
