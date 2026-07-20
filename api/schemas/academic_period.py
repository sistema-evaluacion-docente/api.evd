"""Schemas for request and response bodies related to academic periods."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, model_validator


class AcademicPeriodCreate(BaseModel):
    """Schema for creating an academic period."""

    code: str
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluation_end_date: Optional[date] = None
    final_evaluation_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date debe ser posterior a start_date")
        if self.evaluation_end_date and self.end_date:
            if self.evaluation_end_date > self.end_date:
                raise ValueError("evaluation_end_date no puede ser posterior a end_date")
        if self.final_evaluation_date and self.evaluation_end_date:
            if self.final_evaluation_date > self.evaluation_end_date:
                raise ValueError("final_evaluation_date no puede ser posterior a evaluation_end_date")
        return self


class AcademicPeriodUpdate(BaseModel):
    """Schema for updating an academic period."""

    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluation_end_date: Optional[date] = None
    final_evaluation_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date debe ser posterior a start_date")
        if self.evaluation_end_date and self.end_date:
            if self.evaluation_end_date > self.end_date:
                raise ValueError("evaluation_end_date no puede ser posterior a end_date")
        if self.final_evaluation_date and self.evaluation_end_date:
            if self.final_evaluation_date > self.evaluation_end_date:
                raise ValueError("final_evaluation_date no puede ser posterior a evaluation_end_date")
        return self


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


@dataclass
class AcademicPeriodFilters:
    """Dataclass to hold academic period filters extracted from query parameters."""

    search: str | None = None
    active: bool | None = None


def academic_period_filters(
    search: str | None = Query(default=None, min_length=1),
    active: bool | None = Query(default=None),
) -> AcademicPeriodFilters:
    """Dependency function to extract academic period filters from query parameters."""

    return AcademicPeriodFilters(
        search=search,
        active=active,
    )


AcademicPeriodFiltersDep = Annotated[AcademicPeriodFilters, Depends(academic_period_filters)]
