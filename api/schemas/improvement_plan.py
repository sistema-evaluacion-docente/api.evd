"""
Schemas for request and response bodies related to improvement plans
(Plan de Seguimiento Docente).
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from api.schemas.pagination import Pagination


class TargetType(str, Enum):
    """How an item's compliance is measured against the verification period.

    ``DIMENSION`` targets the overall score of a dimension (e.g. "Desempeño
    Docente"); ``QUESTION`` targets a single question of the evaluation form
    inside that dimension (e.g. "011 - Asiste puntualmente a clase").
    """

    DIMENSION = "DIMENSION"
    QUESTION = "QUESTION"
    PEDAGOGICAL_CATEGORY = "PEDAGOGICAL_CATEGORY"
    OVERALL_AVERAGE = "OVERALL_AVERAGE"
    QUALITATIVE = "QUALITATIVE"


class PlanStatus(str, Enum):
    """Lifecycle status of an improvement plan."""

    BORRADOR = "BORRADOR"
    EN_SEGUIMIENTO = "EN_SEGUIMIENTO"
    RESULTADO_DISPONIBLE = "RESULTADO_DISPONIBLE"
    CERRADO_CUMPLIDO = "CERRADO_CUMPLIDO"
    CERRADO_NO_CUMPLIDO = "CERRADO_NO_CUMPLIDO"
    CERRADO_MANUAL = "CERRADO_MANUAL"


class ItemStatus(str, Enum):
    """Status of a single plan item."""

    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    CUMPLIDO = "CUMPLIDO"
    NO_CUMPLIDO = "NO_CUMPLIDO"


class CloseResult(str, Enum):
    """Result requested when closing a plan."""

    CUMPLIDO = "CUMPLIDO"
    NO_CUMPLIDO = "NO_CUMPLIDO"
    MANUAL = "MANUAL"


class ImprovementPlanItemCreate(BaseModel):
    """Schema for creating/updating a plan item.

    When ``id`` is present on update the existing item is updated; otherwise a
    new item is created. Items omitted from an update payload are removed.
    """

    id: Optional[int] = None
    description: str
    target_type: TargetType = TargetType.QUALITATIVE
    target_ref: Optional[str] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    status: Optional[ItemStatus] = None
    order: Optional[int] = None


class ImprovementPlanCreate(BaseModel):
    """Schema for creating an improvement plan."""

    teacher_id: int
    origin_period_id: int
    verification_period_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    items: list[ImprovementPlanItemCreate] = Field(default_factory=list)


class ImprovementPlanUpdate(BaseModel):
    """Schema for updating an improvement plan and its items.

    If ``items`` is provided it replaces the full item list (add/remove/update).
    """

    title: Optional[str] = None
    description: Optional[str] = None
    verification_period_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    items: Optional[list[ImprovementPlanItemCreate]] = None


class ImprovementPlanClose(BaseModel):
    """Schema for closing a plan."""

    result: CloseResult
    reason: Optional[str] = None


class ImprovementPlanItemOut(BaseModel):
    """Schema for outputting a plan item."""

    id: int
    plan_id: int
    description: str
    target_type: str
    target_ref: Optional[str] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    result_value: Optional[float] = None
    status: str
    order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImprovementPlanCheckpointOut(BaseModel):
    """Schema for outputting a plan checkpoint."""

    id: int
    plan_id: int
    stage: str
    scheduled_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None


class ImprovementPlanOut(BaseModel):
    """Schema for outputting an improvement plan."""

    id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    teacher_avatar_url: Optional[str] = None
    department_id: Optional[int] = None
    origin_period_id: int
    origin_period_code: Optional[str] = None
    verification_period_id: Optional[int] = None
    verification_period_code: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    close_reason: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    progress: int = 0
    suggested_result: Optional[str] = None
    items: list[ImprovementPlanItemOut] = Field(default_factory=list)
    checkpoints: list[ImprovementPlanCheckpointOut] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImprovementPlanDetailResponse(BaseModel):
    """Response envelope for a single improvement plan."""

    status: int
    message: str
    data: Optional[ImprovementPlanOut] = None
    error: Optional[str] = None
    timestamp: datetime
    path: str


class ImprovementPlanListResponse(BaseModel):
    """Response envelope for paginated improvement plans."""

    status: int
    message: str
    data: list[ImprovementPlanOut]
    pagination: Pagination
    error: Optional[str] = None
    timestamp: datetime
    path: str
