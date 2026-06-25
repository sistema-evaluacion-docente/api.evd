"""
User roles pivot model
"""

from sqlalchemy import Column, ForeignKey, Integer

from api.database import Base


class UserRoleModel(Base):
    """
    User roles pivot model
    """

    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True, nullable=False)
