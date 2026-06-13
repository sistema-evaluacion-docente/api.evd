"""
Schemas for request and response bodies related to academic periods.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AcademicPeriodCreate(BaseModel):
    """Schema for creating an academic period."""

    code: str
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluation_end_date: Optional[date] = None
    final_evaluation_date: Optional[date] = None


class AcademicPeriodUpdate(BaseModel):
    """Schema for updating an academic period."""

    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluation_end_date: Optional[date] = None
    final_evaluation_date: Optional[date] = None


class AcademicPeriodStatusUpdate(BaseModel):
    """Schema for activating/deactivating an academic period."""

    active: bool


class AcademicPeriodOut(BaseModel):
    """Schema for outputting an academic period."""

    id: int
    code: str
    name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    evaluation_end_date: Optional[date]
    final_evaluation_date: Optional[date]
    active: Optional[bool]
    created_at: datetime
    updated_at: datetime


class AcademicPeriodDetailResponse(BaseModel):
    """Schema for single academic period response envelope."""

    status: int
    message: str
    data: Optional[AcademicPeriodOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class AcademicPeriodListResponse(BaseModel):
    """Schema for academic periods list response envelope."""

    status: int
    message: str
    data: list[AcademicPeriodOut]
    error: Optional[str] = None
    timestamp: datetime
    path: str
