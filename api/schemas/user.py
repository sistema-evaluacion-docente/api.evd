"""
Schemas for request and response bodies related to users.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    """

    uid: str
    email: str
    username: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = True
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    """
    Schema for updating a user.
    """

    email: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserOut(BaseModel):
    """
    Schema for outputting a user.
    """

    uid: str
    email: str
    username: Optional[str]
    name: Optional[str]
    department_id: Optional[int]
    active: Optional[bool]
    avatar_url: Optional[str]

    created_at: date
    updated_at: date


class TokenUser(BaseModel):
    """
    Schema for the current user.
    """

    uid: str
    email: str
    name: str
    picture: str
