"""
Schemas for request and response bodies related to notifications.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class NotificationType(str, Enum):
    """Allowed notification types."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""

    user_id: int
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    link: Optional[str] = None


class NotificationOut(BaseModel):
    """Schema for outputting a notification."""

    id: int
    user_id: int
    title: str
    message: str
    type: str
    read: bool
    link: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read."""

    ids: list[int]


@dataclass
class NotificationFilters:
    """Dataclass to hold notification filters extracted from query parameters."""

    type: str | None = None
    read: bool | None = None
    search: str | None = None


def notification_filters(
    type: str | None = Query(default=None),
    read: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
) -> NotificationFilters:
    """Dependency function to extract notification filters from query parameters."""

    return NotificationFilters(type=type, read=read, search=search)


NotificationFiltersDep = Annotated[NotificationFilters, Depends(notification_filters)]
