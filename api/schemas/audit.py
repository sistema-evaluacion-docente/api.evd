"""
Schemas for request and response bodies related to audit logs.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class AuditCreate(BaseModel):
    """
    Schema for creating an audit log.
    """

    user_id: Optional[str] = None
    table_name: str
    operation: str
    created_at: Optional[date] = None


class AuditUpdate(BaseModel):
    """
    Schema for updating an audit log.
    """

    user_id: Optional[str] = None
    table_name: Optional[str] = None
    operation: Optional[str] = None
    created_at: Optional[date] = None


class AuditOut(BaseModel):
    """
    Schema for outputting an audit log.
    """

    id: int
    user_id: Optional[str]
    table_name: Optional[str]
    operation: Optional[str]
    created_at: Optional[date]
