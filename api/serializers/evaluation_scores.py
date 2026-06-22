"""Serializer for EvaluationScoreModel to dictionary representation."""

from api.models.evaluation_score import EvaluationScoreModel


def evaluation_score_to_dict(score: EvaluationScoreModel) -> dict:
    """Convert EvaluationScoreModel instance to dictionary."""

    return {
        "id": score.id,
        "evaluation_id": score.evaluation_id,
        "academic_group_id": score.academic_group_id,
        "respondent_count": score.respondent_count,
        "overall_average": score.overall_average,
        "created_at": score.created_at,
        "updated_at": score.updated_at,
    }
