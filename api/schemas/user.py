"""
Schemas for request and response bodies related to users.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    """

    uid: str
    name: str
    username: str
    email: str
    photo_url: Optional[str] = None


class UserUpdate(BaseModel):
    """
    Schema for updating a user.
    """

    name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


class UserOut(BaseModel):
    """
    Schema for outputting a user.
    """

    uid: str
    name: str
    username: str
    email: str
    photo_url: Optional[str]

    created_at: datetime
    updated_at: datetime


class TokenUser(BaseModel):
    """
    Schema for the current user.
    """

    uid: str
    email: str
    name: str
    picture: str

