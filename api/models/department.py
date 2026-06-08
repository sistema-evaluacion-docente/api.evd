"""
Department model
"""

from datetime import date

from sqlalchemy import Boolean, Column, Date, Integer, String

from api.database import Base


class DepartmentModel(Base):
    """
    Department model
    """

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, nullable=False)
    code = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    faculty = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=True, default=True)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today, onupdate=date.today)
