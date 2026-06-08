"""
User model
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)

from api.database import Base


class UserModel(Base):
    """
    User model
    """

    __tablename__ = "users"

    uid = Column(Text, primary_key=True, index=True)  # firebase uid
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    active = Column(Boolean, nullable=True, default=True)
    avatar_url = Column(Text, nullable=True)

    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today, onupdate=date.today)
