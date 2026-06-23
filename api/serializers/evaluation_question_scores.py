"""Serializer for EvaluationQuestionScoreModel to dictionary representation."""

from api.models.evaluation_question_score import EvaluationQuestionScoreModel


def evaluation_question_score_to_dict(question_score: EvaluationQuestionScoreModel) -> dict:
    """Convert EvaluationQuestionScoreModel instance to dictionary."""

    return {
        "id": question_score.id,
        "evaluation_score_id": question_score.evaluation_score_id,
        "question_code": question_score.question_code,
        "score": question_score.score,
    }
