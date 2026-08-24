"""
Schemas for request and response bodies related to improvement plans
(Plan de Seguimiento Docente).
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class ActaStatus(str, Enum):
    """Lifecycle of the acta de compromiso (Formato 2).

    Independent from ``PlanStatus``: the acta freezes when director and teacher
    agree on the terms (``CERRADA``) so it can be printed, and reaches
    ``FIRMADA`` when the signed scan is uploaded back.
    """

    BORRADOR = "BORRADOR"
    CERRADA = "CERRADA"
    FIRMADA = "FIRMADA"


class ItemStatus(str, Enum):
    """Status of a single plan item."""

    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    CUMPLIDO = "CUMPLIDO"
    NO_CUMPLIDO = "NO_CUMPLIDO"


class CheckpointStage(str, Enum):
    """The two formal follow-ups of the official form."""

    PRIMER_SEGUIMIENTO = "PRIMER_SEGUIMIENTO"
    SEGUNDO_SEGUIMIENTO = "SEGUNDO_SEGUIMIENTO"


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
    # "Compromiso" of the official form.
    commitment: Optional[str] = None
    # Section of the official form this item is printed under (1-5).
    aspect: Optional[int] = Field(default=None, ge=1, le=5)
    target_type: TargetType = TargetType.QUALITATIVE
    target_ref: Optional[str] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    status: Optional[ItemStatus] = None
    order: Optional[int] = None
    # Student comments cited as justification for this item.
    comment_ids: Optional[list[int]] = None


class ImprovementPlanCourseCreate(BaseModel):
    """A row of the asignaturas table printed on Formatos 2 and 3."""

    academic_group_id: Optional[int] = None
    course_name: str
    course_code: Optional[str] = None
    group_name: Optional[str] = None
    program_name: Optional[str] = None
    order: Optional[int] = None


class ImprovementPlanCaseReportUpsert(BaseModel):
    """Formato 1 fields — the complaint that originated the plan."""

    complaint: Optional[str] = None
    observations: Optional[str] = None
    committee_act_reference: Optional[str] = None


class ImprovementPlanCheckpointNoteUpsert(BaseModel):
    """One cell of the follow-up matrix (aspect x seguimiento)."""

    aspect: int = Field(ge=1, le=5)
    note: Optional[str] = None


class ImprovementPlanCheckpointUpdate(BaseModel):
    """Schema for filling in one of the two formal seguimientos."""

    scheduled_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    aspect_notes: Optional[list[ImprovementPlanCheckpointNoteUpsert]] = None


class ImprovementPlanCreate(BaseModel):
    """Schema for creating an improvement plan."""

    teacher_id: int
    origin_period_id: int
    verification_period_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    program_name: Optional[str] = None
    faculty_name: Optional[str] = None
    department_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # The acto administrativo backing the agreement. Asked for when the plan is
    # drawn up, so the acta can be closed without a second trip to the detail.
    acta_number: Optional[str] = None
    acta_date: Optional[date] = None
    council_observations: Optional[str] = None
    department_director_observations: Optional[str] = None
    program_director_observations: Optional[str] = None
    items: list[ImprovementPlanItemCreate] = Field(default_factory=list)
    courses: list[ImprovementPlanCourseCreate] = Field(default_factory=list)


class ImprovementPlanUpdate(BaseModel):
    """Schema for updating an improvement plan and its items.

    If ``items`` is provided it replaces the full item list (add/remove/update);
    same for ``courses``.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    verification_period_id: Optional[int] = None
    program_name: Optional[str] = None
    faculty_name: Optional[str] = None
    department_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    acta_number: Optional[str] = None
    acta_date: Optional[date] = None
    council_observations: Optional[str] = None
    department_director_observations: Optional[str] = None
    program_director_observations: Optional[str] = None
    items: Optional[list[ImprovementPlanItemCreate]] = None
    courses: Optional[list[ImprovementPlanCourseCreate]] = None


class ImprovementPlanClose(BaseModel):
    """Schema for closing a plan."""

    result: CloseResult
    reason: Optional[str] = None


class EvidenceStatus(str, Enum):
    """Review state of a single submitted evidence."""

    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class EvidenceRequestStatus(str, Enum):
    """State of a deliverable the director asked the teacher for.

    A rejection sends the request back to PENDIENTE so the teacher can submit
    again.
    """

    PENDIENTE = "PENDIENTE"
    EN_REVISION = "EN_REVISION"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class ImprovementPlanEvidenceRequestCreate(BaseModel):
    """Schema for asking the teacher for a specific deliverable."""

    title: str
    description: Optional[str] = None
    item_id: Optional[int] = None
    due_date: Optional[date] = None


class ImprovementPlanEvidenceRequestUpdate(BaseModel):
    """Schema for editing a pending evidence request."""

    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[EvidenceRequestStatus] = None


class ImprovementPlanEvidenceReview(BaseModel):
    """Schema for the director's verdict on a submitted evidence."""

    status: EvidenceStatus
    comment: Optional[str] = None


class ImprovementPlanEvidenceCommentCreate(BaseModel):
    """Schema for posting a message on an evidence request thread."""

    body: str


class ImprovementPlanEvidenceCommentOut(BaseModel):
    """Schema for outputting a message of an evidence request thread."""

    id: int
    request_id: int
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    body: str
    is_system: bool = False
    created_at: Optional[datetime] = None


class ImprovementPlanItemCommentOut(BaseModel):
    """A student comment cited as justification of an item."""

    comment_id: int
    original_text: Optional[str] = None
    risk_level_name: Optional[str] = None
    risk_score: Optional[float] = None


class ImprovementPlanItemOut(BaseModel):
    """Schema for outputting a plan item."""

    id: int
    plan_id: int
    description: str
    commitment: Optional[str] = None
    aspect: Optional[int] = None
    target_type: str
    target_ref: Optional[str] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    result_value: Optional[float] = None
    status: str
    order: int
    comments: list[ImprovementPlanItemCommentOut] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImprovementPlanCheckpointNoteOut(BaseModel):
    """Schema for outputting one follow-up cell."""

    id: int
    aspect: int
    note: Optional[str] = None


class ImprovementPlanCheckpointOut(BaseModel):
    """Schema for outputting a plan checkpoint."""

    id: int
    plan_id: int
    stage: str
    scheduled_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    aspect_notes: list[ImprovementPlanCheckpointNoteOut] = Field(default_factory=list)


class ImprovementPlanCourseOut(BaseModel):
    """Schema for outputting an asignatura row."""

    id: int
    plan_id: int
    academic_group_id: Optional[int] = None
    course_name: str
    course_code: Optional[str] = None
    group_name: Optional[str] = None
    program_name: Optional[str] = None
    order: int


class ImprovementPlanCaseReportOut(BaseModel):
    """Schema for outputting the Formato 1 case report."""

    id: int
    plan_id: int
    reported_by: Optional[int] = None
    complaint: Optional[str] = None
    observations: Optional[str] = None
    committee_act_reference: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImprovementPlanDocumentOut(BaseModel):
    """Schema for outputting a generated/signed official form."""

    id: int
    plan_id: int
    format_type: str
    generated_at: Optional[datetime] = None
    generated_by: Optional[int] = None
    signed_at: Optional[datetime] = None
    signed_by: Optional[int] = None
    signed_filename: Optional[str] = None
    has_generated: bool = False
    has_signed: bool = False


class ImprovementPlanEvidenceOut(BaseModel):
    """Schema for outputting a plan evidence (PDF attached as compliance proof)."""

    id: int
    plan_id: int
    item_id: Optional[int] = None
    request_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    uploader_name: Optional[str] = None
    description: Optional[str] = None
    file_url: str
    status: str = "PENDIENTE"
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ImprovementPlanEvidenceRequestOut(BaseModel):
    """Schema for outputting an evidence request with its thread."""

    id: int
    plan_id: int
    item_id: Optional[int] = None
    requested_by: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    due_date: Optional[date] = None
    evidences: list[ImprovementPlanEvidenceOut] = Field(default_factory=list)
    comments: list[ImprovementPlanEvidenceCommentOut] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImprovementPlanVerificationCourseOut(BaseModel):
    """One subject of the verification period, for the indicator verified."""

    id: int
    academic_group_id: Optional[int] = None
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    group_name: Optional[str] = None
    result_value: Optional[float] = None
    met: bool = False


class ImprovementPlanVerificationItemOut(BaseModel):
    """One agreed target, measured again a semester later."""

    id: int
    item_id: Optional[int] = None
    target_type: str
    target_ref: Optional[str] = None
    target_value: Optional[float] = None
    result_value: Optional[float] = None
    met: Optional[bool] = None
    courses: list[ImprovementPlanVerificationCourseOut] = Field(default_factory=list)


class ImprovementPlanVerificationCommentOut(BaseModel):
    """A student comment bringing back the complaint behind a commitment."""

    id: int
    item_id: Optional[int] = None
    comment_id: int
    original_text: Optional[str] = None
    pedagogical_category_id: Optional[int] = None
    category_name: Optional[str] = None
    risk_level_name: Optional[str] = None
    is_alert: bool = False


class ImprovementPlanVerificationOut(BaseModel):
    """What the following semester said about a plan.

    ``result`` is what the grades say — MEJORO / NO_MEJORO / SIN_DATOS — and is
    never the closing the director signed, which lives in ``status``.
    """

    id: int
    plan_id: int
    period_id: int
    period_code: Optional[str] = None
    result: str
    scores_verified_at: Optional[datetime] = None
    comments_verified_at: Optional[datetime] = None
    items: list[ImprovementPlanVerificationItemOut] = Field(default_factory=list)
    comment_findings: list[ImprovementPlanVerificationCommentOut] = Field(
        default_factory=list
    )
    created_at: Optional[datetime] = None


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
    program_name: Optional[str] = None
    faculty_name: Optional[str] = None
    department_name: Optional[str] = None
    status: str
    close_reason: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    acta_number: Optional[str] = None
    acta_date: Optional[date] = None
    acta_status: str = ActaStatus.BORRADOR.value
    acta_closed_at: Optional[datetime] = None
    acta_closed_by: Optional[int] = None
    acta_locked: bool = False
    council_observations: Optional[str] = None
    department_director_observations: Optional[str] = None
    program_director_observations: Optional[str] = None
    has_acta: bool = False
    progress: int = 0
    verification: Optional[ImprovementPlanVerificationOut] = None
    items: list[ImprovementPlanItemOut] = Field(default_factory=list)
    checkpoints: list[ImprovementPlanCheckpointOut] = Field(default_factory=list)
    evidences: list[ImprovementPlanEvidenceOut] = Field(default_factory=list)
    courses: list[ImprovementPlanCourseOut] = Field(default_factory=list)
    case_report: Optional[ImprovementPlanCaseReportOut] = None
    documents: list[ImprovementPlanDocumentOut] = Field(default_factory=list)
    evidence_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
