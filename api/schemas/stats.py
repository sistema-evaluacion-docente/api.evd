"""
Schemas for request and response bodies related to statistics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DepartmentPeriodStat(BaseModel):
    """Statistics for a department in a given academic period."""

    department_id: int
    department_name: str
    department_code: str
    academic_period_id: int
    academic_period_code: str
    academic_period_name: Optional[str]
    global_average: Optional[Decimal]
    total_respondents: int
    evaluation_count: int


class StatsListResponse(BaseModel):
    """Schema for statistics list response envelope."""

    status: int
    message: str
    data: list[DepartmentPeriodStat]
    error: Optional[str] = None
    timestamp: datetime
    path: str
