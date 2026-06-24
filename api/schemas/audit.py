"""
Schemas for request and response bodies related to audit logs.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from api.schemas.pagination import Pagination


class AuditCreate(BaseModel):
    """
    Schema for creating an audit log.
    """

    user_id: Optional[str] = None
    table_name: str
    operation: str
    created_at: Optional[datetime] = None


class AuditUpdate(BaseModel):
    """
    Schema for updating an audit log.
    """

    user_id: Optional[str] = None
    table_name: Optional[str] = None
    operation: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditOut(BaseModel):
    """
    Schema for outputting an audit log.
    """

    id: int
    user_id: Optional[str]
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    table_name: Optional[str]
    operation: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class AuditDetailResponse(BaseModel):
    """Response envelope for a single audit log."""

    data: Optional[AuditOut]
    error: Optional[str]
    status: int
    timestamp: datetime


class AuditListResponse(BaseModel):
    """Response envelope for paginated audit logs."""

    data: list[AuditOut]
    pagination: Pagination
    error: Optional[str]
    status: int
    timestamp: datetime
