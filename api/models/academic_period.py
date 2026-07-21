"""
Academic period model
"""

import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class AcademicPeriodModel(Base):
    """
    Academic period model
    """

    __tablename__ = "academic_periods"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    evaluation_end_date = Column(Date, nullable=True)
    final_evaluation_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=True, default=False)

    academic_groups = relationship("AcademicGroupModel", back_populates="academic_period")

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
