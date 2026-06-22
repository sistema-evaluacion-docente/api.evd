"""Serializer for CommentModel to dictionary representation."""

from api.models.comment import CommentModel


def comment_to_dict(comment: CommentModel) -> dict:
    """Convert CommentModel instance to dictionary."""

    return {
        "id": comment.id,
        "teacher_id": comment.teacher_id,
        "evaluation_id": comment.evaluation_id,
        "academic_groups_id": comment.academic_groups_id,
        "original_text": comment.original_text,
        "risk_level": comment.risk_level,
        "pedagogical_category_id": comment.pedagogical_category_id,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
