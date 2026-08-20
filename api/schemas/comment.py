"""
Schemas for request and response bodies related to comments.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, model_validator


class RiskLevelOut(BaseModel):
    """Schema for risk level output."""

    id: int
    name: str
    color_hex: Optional[str] = None


class PedagogicalCategoryOut(BaseModel):
    """Schema for pedagogical category output."""

    id: int
    name: str
    description: Optional[str] = None
    color_hex: Optional[str] = None


class PedagogicalCategoryScoreOut(PedagogicalCategoryOut):
    """Pedagogical category output with the confidence score of this assignment."""

    score: Optional[float] = None


class CommentOut(BaseModel):
    """Schema for outputting a comment."""

    id: int
    teacher_id: Optional[int]
    evaluation_id: Optional[int]
    academic_groups_id: Optional[int]
    group_name: Optional[str] = None
    teacher_name: Optional[str] = None
    teacher_avatar_url: Optional[str] = None
    course_name: Optional[str] = None
    original_text: Optional[str]
    risk_level: Optional[RiskLevelOut] = None
    risk_score: Optional[float] = None
    pedagogical_categories: list[PedagogicalCategoryScoreOut] = []
    risk_level_modified_by_director: bool = False
    pedagogical_category_modified_by_director: bool = False
    risk_level_ai_model: Optional[str] = None
    pedagogical_category_ai_model: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CommentUpdate(BaseModel):
    """Schema for updating a comment's risk level and/or pedagogical categories.

    Only a department director may perform this update; each field actually
    provided is flagged as modified by the director. ``pedagogical_category_ids``
    replaces the comment's full set of categories — pass one, several, or an
    empty list to clear them all.
    """

    risk_level: Optional[int] = None
    pedagogical_category_ids: Optional[list[int]] = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        """Validate that at least one of the two fields is provided."""

        if self.risk_level is None and self.pedagogical_category_ids is None:
            raise ValueError(
                "Debe proporcionar al menos risk_level o pedagogical_category_ids"
            )
        return self


@dataclass
class CommentFilters:
    """Dataclass to hold comment filters extracted from query parameters."""

    evaluation_id: int | None = None
    teacher_id: int | None = None
    academic_groups_id: int | None = None
    academic_period_id: int | None = None
    risk_level: int | None = None
    pedagogical_category_id: int | None = None
    search: str | None = None


def comment_filters(
    evaluation_id: int | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    academic_groups_id: int | None = Query(default=None),
    academic_period_id: int | None = Query(default=None),
    risk_level: int | None = Query(default=None),
    pedagogical_category_id: int | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
) -> CommentFilters:
    """Dependency function to extract comment filters from query parameters."""

    return CommentFilters(
        evaluation_id=evaluation_id,
        teacher_id=teacher_id,
        academic_groups_id=academic_groups_id,
        academic_period_id=academic_period_id,
        risk_level=risk_level,
        pedagogical_category_id=pedagogical_category_id,
        search=search,
    )


CommentFiltersDep = Annotated[CommentFilters, Depends(comment_filters)]
