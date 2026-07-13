"""Serializers for improvement plan models to dictionary representation."""

from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_item import ImprovementPlanItemModel


def _to_float(value) -> float | None:
    return float(value) if value is not None else None


def improvement_plan_item_to_dict(item: ImprovementPlanItemModel) -> dict:
    """Convert an ImprovementPlanItemModel instance to a dictionary."""

    return {
        "id": item.id,
        "plan_id": item.plan_id,
        "description": item.description,
        "target_type": item.target_type,
        "target_ref": item.target_ref,
        "baseline_value": _to_float(item.baseline_value),
        "target_value": _to_float(item.target_value),
        "result_value": _to_float(item.result_value),
        "status": item.status,
        "order": item.order,
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
    }


def _compute_progress(items: list[ImprovementPlanItemModel]) -> int:
    """Percentage of items marked CUMPLIDO over the total number of items."""

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
) -> dict:
    """Convert an ImprovementPlanModel instance to a dictionary."""

    items = list(plan.items) if include_relations else []
    checkpoints = list(plan.checkpoints) if include_relations else []

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
        "status": plan.status,
        "close_reason": plan.close_reason,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "created_by": plan.created_by,
        "closed_at": plan.closed_at,
        "progress": _compute_progress(items),
        "suggested_result": suggested_result,
        "items": [improvement_plan_item_to_dict(i) for i in items],
        "checkpoints": [
            improvement_plan_checkpoint_to_dict(c) for c in checkpoints
        ],
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
