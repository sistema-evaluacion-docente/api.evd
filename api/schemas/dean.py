"""Schemas for Dean entity."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AssignDeanRequest(BaseModel):
    """Schema for assigning a dean to a faculty."""

    user_id: int


class DeanOut(BaseModel):
    """Schema for outputting dean information."""

    id: int
    user_id: int
    faculty_id: int
    active: bool
    created_at: datetime
    updated_at: datetime
