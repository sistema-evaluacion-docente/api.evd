"""
User roles pivot model
"""

from sqlalchemy import Column, ForeignKey, Integer, Text

from api.database import Base


class UserRoleModel(Base):
    """
    User roles pivot model
    """

    __tablename__ = "user_roles"

    user_id = Column(Text, ForeignKey("users.uid"), primary_key=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True, nullable=False)
