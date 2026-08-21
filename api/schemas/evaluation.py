"""
Schemas for request and response bodies related to evaluations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, NamedTuple, Optional

from fastapi import Depends, Query
from pydantic import BaseModel

from api.schemas.comparison import DimensionComparisonDetail
from api.schemas.evaluation_summary import DimensionAverageItem


class UploadedPdf(NamedTuple):
    """A PDF as it arrives in the upload request.

    Lets the service validate and store the file without knowing anything
    about FastAPI's ``UploadFile``."""

    filename: str | None
    content: bytes


class EvaluationStatusUpdate(BaseModel):
    """Schema for activating/deactivating an evaluation."""

    active: bool


class EvaluationPeriodComparison(BaseModel):
    """Comparison of this evaluation's averages against the department's
    evaluation in the immediately preceding academic period."""

    previous_period_code: Optional[str]
    previous_period_name: Optional[str]
    current_average: Optional[float]
    old_average: Optional[float]
    average_difference: Optional[float]
    dimensions: list[DimensionComparisonDetail]


class EvaluationOut(BaseModel):
    """Schema for outputting an evaluation."""

    id: int
    user_id: Optional[int]
    academic_period_id: Optional[int]
    academic_period_name: Optional[str]
    academic_period_code: Optional[str]
    department_id: Optional[int]
    pdf_url: Optional[str]
    pdf_urls: list[str] = []
    modality: Optional[str] = None
    active: Optional[bool]
    status: Optional[str]
    ai_status: Optional[str] = None
    count: Optional[int]
    overall_average: Optional[float] = None
    comments_risk_counts: Optional[dict[str, int]] = None
    dimension_averages: Optional[list[DimensionAverageItem]] = None
    comparison: Optional[EvaluationPeriodComparison] = None
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
