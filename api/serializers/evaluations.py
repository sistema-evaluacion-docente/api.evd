"""Serializer for EvaluationModel to dictionary representation."""

from api.models.evaluation import EvaluationModel


def evaluation_to_dict(evaluation: EvaluationModel) -> dict:
    """Convert EvaluationModel instance to dictionary."""

    return {
        "id": evaluation.id,
        "user_id": evaluation.user_id,
        "academic_period_id": evaluation.academic_period_id,
        "academic_period_name": evaluation.academic_period.name if evaluation.academic_period else None,
        "academic_period_code": evaluation.academic_period.code if evaluation.academic_period else None,
        "department_id": evaluation.department_id,
        "pdf_url": evaluation.pdf_url,
        "active": evaluation.active,
        "status": evaluation.status,
        "ai_status": evaluation.ai_status,
        "count": evaluation.count,
        "created_at": evaluation.created_at,
        "updated_at": evaluation.updated_at,
    }
