"""
User model
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
)

from api.database import Base


class UserModel(Base):
    """
    User model
    """

    __tablename__ = "users"

    uid = Column(String, primary_key=True, index=True)  # firebase uid
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    photo_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
