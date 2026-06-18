"""
Schemas for request and response bodies related to settings.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from api.schemas.pagination import Pagination


class SettingCreate(BaseModel):
    key: str
    value: str
    value_type: str = "NUMBER"
    description: Optional[str] = None
    change_reason: Optional[str] = None


class SettingUpdate(BaseModel):
    value: str
    change_reason: Optional[str] = None


class SettingOut(BaseModel):
    id: int
    key: str
    value: str
    value_type: str
    description: Optional[str]
    changed_by: Optional[str]
    effective_from: datetime
    created_at: datetime
    updated_at: datetime


class SettingHistoryOut(BaseModel):
    id: int
    key: str
    old_value: Optional[str]
    new_value: str
    changed_by: Optional[str]
    change_reason: Optional[str]
    changed_at: datetime


class SettingDetailResponse(BaseModel):
    status: int
    message: str
    data: Optional[SettingOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class SettingListResponse(BaseModel):
    status: int
    message: str
    data: list[SettingOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str


class SettingHistoryListResponse(BaseModel):
    status: int
    message: str
    data: list[SettingHistoryOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str
