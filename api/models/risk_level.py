"""
RiskLevel model
"""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class RiskLevelModel(Base):
    """Risk level catalogue — BAJO, MEDIO, ALTO assigned by the AI component."""

    __tablename__ = "risk_levels"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color_hex = Column(String(50), nullable=True)

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
