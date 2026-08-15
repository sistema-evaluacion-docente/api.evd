"""Serializers for improvement plan models to dictionary representation."""

from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_case_report import ImprovementPlanCaseReportModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_course import ImprovementPlanCourseModel
from api.models.improvement_plan_document import ImprovementPlanDocumentModel
from api.models.improvement_plan_evidence import ImprovementPlanEvidenceModel
from api.models.improvement_plan_item import ImprovementPlanItemModel

# The acta content is frozen from this status onwards.
LOCKED_ACTA_STATUSES = ("CERRADA", "FIRMADA")


def _to_float(value) -> float | None:
    return float(value) if value is not None else None


def improvement_plan_item_comment_to_dict(link) -> dict:
    """Convert a cited student comment to a dictionary.

    ``link`` is an ImprovementPlanItemCommentModel with its ``comment`` loaded.
    """

    comment = link.comment

    return {
        "comment_id": link.comment_id,
        "original_text": comment.original_text if comment else None,
        "risk_level_name": (
            comment.risk_level_rel.name
            if comment is not None and comment.risk_level_rel is not None
            else None
        ),
        "risk_score": comment.risk_score if comment else None,
    }


def improvement_plan_item_to_dict(item: ImprovementPlanItemModel) -> dict:
    """Convert an ImprovementPlanItemModel instance to a dictionary."""

    return {
        "id": item.id,
        "plan_id": item.plan_id,
        "description": item.description,
        "commitment": item.commitment,
        "aspect": item.aspect,
        "target_type": item.target_type,
        "target_ref": item.target_ref,
        "baseline_value": _to_float(item.baseline_value),
        "target_value": _to_float(item.target_value),
        "result_value": _to_float(item.result_value),
        "status": item.status,
        "order": item.order,
        "comments": [
            improvement_plan_item_comment_to_dict(link) for link in item.comment_links
        ],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def improvement_plan_checkpoint_to_dict(
    checkpoint: ImprovementPlanCheckpointModel,
) -> dict:
    """Convert an ImprovementPlanCheckpointModel instance to a dictionary."""

    return {
        "id": checkpoint.id,
        "plan_id": checkpoint.plan_id,
        "stage": checkpoint.stage,
        "scheduled_date": checkpoint.scheduled_date,
        "completed_at": checkpoint.completed_at,
        "status": checkpoint.status,
        "notes": checkpoint.notes,
        "aspect_notes": [
            {"id": note.id, "aspect": note.aspect, "note": note.note}
            for note in checkpoint.aspect_notes
        ],
    }


def improvement_plan_course_to_dict(course: ImprovementPlanCourseModel) -> dict:
    """Convert an ImprovementPlanCourseModel instance to a dictionary."""

    return {
        "id": course.id,
        "plan_id": course.plan_id,
        "academic_group_id": course.academic_group_id,
        "course_name": course.course_name,
        "course_code": course.course_code,
        "group_name": course.group_name,
        "program_name": course.program_name,
        "order": course.order,
    }


def improvement_plan_case_report_to_dict(
    case_report: ImprovementPlanCaseReportModel,
) -> dict:
    """Convert an ImprovementPlanCaseReportModel instance to a dictionary."""

    return {
        "id": case_report.id,
        "plan_id": case_report.plan_id,
        "reported_by": case_report.reported_by,
        "complaint": case_report.complaint,
        "observations": case_report.observations,
        "committee_act_reference": case_report.committee_act_reference,
        "created_at": case_report.created_at,
        "updated_at": case_report.updated_at,
    }


def improvement_plan_document_to_dict(
    document: ImprovementPlanDocumentModel,
) -> dict:
    """Convert an ImprovementPlanDocumentModel instance to a dictionary.

    The stored paths are deliberately left out: files are served through
    permission-checked download endpoints, never as public URLs.
    """

    return {
        "id": document.id,
        "plan_id": document.plan_id,
        "format_type": document.format_type,
        "generated_at": document.generated_at,
        "generated_by": document.generated_by,
        "signed_at": document.signed_at,
        "signed_by": document.signed_by,
        "has_generated": document.generated_pdf_url is not None,
        "has_signed": document.signed_pdf_url is not None,
    }


def improvement_plan_evidence_to_dict(
    evidence: ImprovementPlanEvidenceModel,
    uploader_name: str | None = None,
) -> dict:
    """Convert an ImprovementPlanEvidenceModel instance to a dictionary."""

    return {
        "id": evidence.id,
        "plan_id": evidence.plan_id,
        "item_id": evidence.item_id,
        "request_id": evidence.request_id,
        "uploaded_by": evidence.uploaded_by,
        "uploader_name": uploader_name,
        "description": evidence.description,
        "file_url": evidence.file_url,
        "status": evidence.status,
        "reviewed_by": evidence.reviewed_by,
        "reviewed_at": evidence.reviewed_at,
        "created_at": evidence.created_at,
    }


def improvement_plan_evidence_comment_to_dict(
    comment, author_name: str | None = None
) -> dict:
    """Convert a message of an evidence request thread to a dictionary."""

    return {
        "id": comment.id,
        "request_id": comment.request_id,
        "author_id": comment.author_id,
        "author_name": author_name,
        "body": comment.body,
        "is_system": comment.is_system,
        "created_at": comment.created_at,
    }


def improvement_plan_evidence_request_to_dict(
    request,
    author_names: dict[int, str] | None = None,
) -> dict:
    """Convert an evidence request, with its evidences and thread, to a dict."""

    names = author_names or {}

    return {
        "id": request.id,
        "plan_id": request.plan_id,
        "item_id": request.item_id,
        "requested_by": request.requested_by,
        "title": request.title,
        "description": request.description,
        "status": request.status,
        "due_date": request.due_date,
        "evidences": [
            improvement_plan_evidence_to_dict(
                e, uploader_name=names.get(e.uploaded_by)
            )
            for e in request.evidences
        ],
        "comments": [
            improvement_plan_evidence_comment_to_dict(
                c, author_name=names.get(c.author_id)
            )
            for c in request.comments
        ],
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }


def _compute_progress(status: str, items: list[ImprovementPlanItemModel]) -> int:
    """Percentage of items marked CUMPLIDO over the total number of items.

    A plan closed as CUMPLIDO is always at 100%: the director confirmed the
    whole plan was fulfilled, regardless of how each item was left."""

    if status == "CERRADO_CUMPLIDO":
        return 100

    if not items:
        return 0

    fulfilled = sum(1 for i in items if i.status == "CUMPLIDO")

    return round(100 * fulfilled / len(items))


def improvement_plan_to_dict(
    plan: ImprovementPlanModel,
    *,
    teacher_name: str | None = None,
    teacher_avatar_url: str | None = None,
    origin_period_code: str | None = None,
    verification_period_code: str | None = None,
    suggested_result: str | None = None,
    include_relations: bool = True,
    evidence_uploader_names: dict[int, str] | None = None,
) -> dict:
    """Convert an ImprovementPlanModel instance to a dictionary.

    ``evidence_uploader_names`` maps user ids to display names so each
    evidence carries who attached it."""

    items = list(plan.items) if include_relations else []
    checkpoints = list(plan.checkpoints) if include_relations else []
    evidences = list(plan.evidences) if include_relations else []
    courses = list(plan.courses) if include_relations else []
    documents = list(plan.documents) if include_relations else []
    uploader_names = evidence_uploader_names or {}

    signed_acta = next(
        (
            d
            for d in documents
            if d.format_type == "FORMATO_2" and d.signed_pdf_url is not None
        ),
        None,
    )

    return {
        "id": plan.id,
        "teacher_id": plan.teacher_id,
        "teacher_name": teacher_name,
        "teacher_avatar_url": teacher_avatar_url,
        "department_id": plan.department_id,
        "origin_period_id": plan.origin_period_id,
        "origin_period_code": origin_period_code,
        "verification_period_id": plan.verification_period_id,
        "verification_period_code": verification_period_code,
        "title": plan.title,
        "description": plan.description,
        "program_name": plan.program_name,
        "faculty_name": plan.faculty_name,
        "department_name": plan.department_name,
        "status": plan.status,
        "close_reason": plan.close_reason,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "created_by": plan.created_by,
        "closed_at": plan.closed_at,
        "acta_number": plan.acta_number,
        "acta_date": plan.acta_date,
        "acta_status": plan.acta_status,
        "acta_closed_at": plan.acta_closed_at,
        "acta_closed_by": plan.acta_closed_by,
        "acta_locked": plan.acta_status in LOCKED_ACTA_STATUSES,
        "council_observations": plan.council_observations,
        "department_director_observations": plan.department_director_observations,
        "program_director_observations": plan.program_director_observations,
        "has_acta": signed_acta is not None,
        "progress": _compute_progress(plan.status, items),
        "suggested_result": suggested_result,
        "items": [improvement_plan_item_to_dict(i) for i in items],
        "checkpoints": [
            improvement_plan_checkpoint_to_dict(c) for c in checkpoints
        ],
        "evidences": [
            improvement_plan_evidence_to_dict(
                e, uploader_name=uploader_names.get(e.uploaded_by)
            )
            for e in evidences
        ],
        "courses": [improvement_plan_course_to_dict(c) for c in courses],
        "case_report": (
            improvement_plan_case_report_to_dict(plan.case_report)
            if include_relations and plan.case_report
            else None
        ),
        "documents": [improvement_plan_document_to_dict(d) for d in documents],
        "evidence_count": len(evidences),
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
