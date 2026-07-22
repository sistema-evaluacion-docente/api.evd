"""Schemas for audit log request and response bodies."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class UserSummary(BaseModel):
    """Lightweight user schema for audit actor."""

    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class AuditCreate(BaseModel):
    """Internal schema for creating an audit log."""

    user_id: Optional[int] = None
    table_name: str
    operation: str
    element: Optional[str] = None
    description: Optional[str] = None


class AuditOut(BaseModel):
    """Schema for outputting an audit log."""

    id: int
    user_id: Optional[int]
    user: Optional[UserSummary] = None
    table_name: Optional[str]
    operation: Optional[str]
    element: Optional[str]
    description: Optional[str]
    element_data: Optional[dict] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


@dataclass
class AuditFilters:
    """Dataclass to hold audit filters extracted from query parameters."""

    actor_id: Optional[int] = None
    entity_name: Optional[str] = None
    operation: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None


def audit_filters(
    actor_id: Optional[int] = Query(
        default=None, description="Filter by actor user ID"
    ),
    entity_name: Optional[str] = Query(
        default=None, description="Filter by entity/table name"
    ),
    operation: Optional[str] = Query(
        default=None, description="Filter by operation type"
    ),
    date_from: Optional[datetime] = Query(
        default=None, description="Filter from date (inclusive)"
    ),
    date_to: Optional[datetime] = Query(
        default=None, description="Filter to date (inclusive)"
    ),
    search: Optional[str] = Query(
        default=None, min_length=1, description="Search in element and description"
    ),
) -> AuditFilters:
    """Dependency function to extract audit filters from query parameters."""

    return AuditFilters(
        actor_id=actor_id,
        entity_name=entity_name,
        operation=operation,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


AuditFiltersDep = Annotated[AuditFilters, Depends(audit_filters)]
