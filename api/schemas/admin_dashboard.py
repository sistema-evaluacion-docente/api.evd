"""
Schemas for admin dashboard summary endpoint.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdminDashboardCounts(BaseModel):
    departments: int
    faculties: int
    users: int
    active_users: int
    teachers: int
    evaluations: int
    academic_periods: int
    active_periods: int


class RecentAuditItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    table_name: Optional[str] = None
    operation: Optional[str] = None
    element: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class PeriodItem(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: bool


class AdminDashboardData(BaseModel):
    counts: AdminDashboardCounts
    recent_audits: list[RecentAuditItem]
    periods: list[PeriodItem]


class AdminDashboardResponse(BaseModel):
    status: int
    message: str
    data: AdminDashboardData
    error: Optional[str] = None
    timestamp: datetime
    path: str
