"""
Schemas for request and response bodies related to evaluations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel


class EvaluationStatusUpdate(BaseModel):
    """Schema for activating/deactivating an evaluation."""

    active: bool


class EvaluationOut(BaseModel):
    """Schema for outputting an evaluation."""

    id: int
    user_id: Optional[int]
    academic_period_id: Optional[int]
    academic_period_name: Optional[str]
    academic_period_code: Optional[str]
    department_id: Optional[int]
    pdf_url: Optional[str]
    active: Optional[bool]
    status: Optional[str]
    ai_status: Optional[str] = None
    count: Optional[int]
    overall_average: Optional[float] = None
    created_at: datetime
    updated_at: datetime


@dataclass
class EvaluationFilters:
    """Dataclass to hold evaluation filters extracted from query parameters."""

    search: str | None = None
    period_id: int | None = None
    department_id: int | None = None
    status: str | None = None
    ai_status: str | None = None
    active: bool | None = None
    sort_by: str | None = None


def evaluation_filters(
    search: str | None = Query(default=None, min_length=1),
    period_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    ai_status: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str | None = Query(default=None),
) -> EvaluationFilters:
    """Dependency function to extract evaluation filters from query parameters."""

    return EvaluationFilters(
        search=search,
        period_id=period_id,
        department_id=department_id,
        status=status,
        ai_status=ai_status,
        active=active,
        sort_by=sort_by,
    )


EvaluationFiltersDep = Annotated[EvaluationFilters, Depends(evaluation_filters)]
