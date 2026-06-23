"""
Schemas for request and response bodies related to comments.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CommentOut(BaseModel):
    """Schema for outputting a comment."""

    id: int
    teacher_id: Optional[int]
    evaluation_id: Optional[int]
    academic_groups_id: Optional[int]
    original_text: Optional[str]
    risk_level: Optional[int]
    pedagogical_category_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class CommentDetailResponse(BaseModel):
    """Schema for single comment response envelope."""

    status: int
    message: str
    data: Optional[CommentOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class CommentListResponse(BaseModel):
    """Schema for comments list response envelope."""

    status: int
    message: str
    data: list[CommentOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
