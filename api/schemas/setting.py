"""Schemas for request and response bodies related to settings."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class SettingCreate(BaseModel):
    """Schema for creating a setting."""

    key: str
    value: str
    value_type: str = "STRING"
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    """Schema for updating a setting."""

    value: str
    change_reason: Optional[str] = None


class SettingOut(BaseModel):
    """Schema for outputting a setting."""

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
    """Schema for outputting a setting history entry."""

    id: int
    key: str
    old_value: Optional[str]
    new_value: str
    changed_by: Optional[str]
    change_reason: Optional[str]
    changed_at: datetime


@dataclass
class SettingFilters:
    """Dataclass to hold setting filters extracted from query parameters."""

    search: str | None = None
    value_type: str | None = None


def setting_filters(
    search: str | None = Query(default=None, min_length=1),
    value_type: str | None = Query(default=None),
) -> SettingFilters:
    """Dependency function to extract setting filters from query parameters."""

    return SettingFilters(
        search=search,
        value_type=value_type,
    )


SettingFiltersDep = Annotated[SettingFilters, Depends(setting_filters)]
