"""Schemas for request and response bodies related to settings."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class SettingScope(str, Enum):
    """Who a setting belongs to."""

    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"


class SettingCreate(BaseModel):
    """Schema for creating a setting.

    ``department_id`` is only honoured for an ADMIN: a director always creates
    settings for its own department, whatever the payload says.
    """

    key: str
    value: str
    value_type: str = "STRING"
    description: Optional[str] = None
    department_id: Optional[int] = None


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
    department_id: Optional[int]
    department_name: Optional[str] = None
    scope: SettingScope
    changed_by: Optional[str]
    changed_by_name: Optional[str]
    changed_by_avatar_url: Optional[str]
    effective_from: datetime
    created_at: datetime
    updated_at: datetime


class SettingHistoryOut(BaseModel):
    """Schema for outputting a setting history entry."""

    id: int
    key: str
    old_value: Optional[str]
    new_value: str
    department_id: Optional[int]
    changed_by: Optional[str]
    changed_by_name: Optional[str]
    changed_by_avatar_url: Optional[str]
    change_reason: Optional[str]
    changed_at: datetime


@dataclass
class SettingFilters:
    """Dataclass to hold setting filters extracted from query parameters.

    ``department_id`` narrows the list to one department; ``include_global``
    decides whether the institutional settings come along with it. The service
    overrides ``department_id`` for a director so it can only ever be its own.
    """

    search: str | None = None
    value_type: str | None = None
    department_id: int | None = None
    include_global: bool = True


def setting_filters(
    search: str | None = Query(default=None, min_length=1),
    value_type: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    include_global: bool = Query(default=True),
) -> SettingFilters:
    """Dependency function to extract setting filters from query parameters."""

    return SettingFilters(
        search=search,
        value_type=value_type,
        department_id=department_id,
        include_global=include_global,
    )


SettingFiltersDep = Annotated[SettingFilters, Depends(setting_filters)]
