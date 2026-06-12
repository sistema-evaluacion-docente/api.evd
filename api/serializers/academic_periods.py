"""Serializer for AcademicPeriodModel to dictionary representation."""

from api.models.academic_period import AcademicPeriodModel


def academic_period_to_dict(period: AcademicPeriodModel) -> dict:
    """Convert AcademicPeriodModel instance to dictionary."""

    return {
        "id": period.id,
        "code": period.code,
        "name": period.name,
        "start_date": period.start_date,
        "end_date": period.end_date,
        "evaluation_end_date": period.evaluation_end_date,
        "final_evaluation_date": period.final_evaluation_date,
        "active": period.active,
        "created_at": period.created_at,
        "updated_at": period.updated_at,
    }
