"""Serializer for CommentModel to dictionary representation."""

from typing import Optional

from api.models.comment import CommentModel


def comment_to_dict(
    comment: CommentModel,
    group_name: Optional[str] = None,
    teacher_name: Optional[str] = None,
    teacher_avatar_url: Optional[str] = None,
    course_name: Optional[str] = None,
) -> dict:
    """Convert CommentModel instance to dictionary."""

    risk = comment.risk_level_rel

    return {
        "id": comment.id,
        "teacher_id": comment.teacher_id,
        "evaluation_id": comment.evaluation_id,
        "academic_groups_id": comment.academic_groups_id,
        "group_name": group_name,
        "teacher_name": teacher_name,
        "teacher_avatar_url": teacher_avatar_url,
        "course_name": course_name,
        "original_text": comment.original_text,
        "risk_level": (
            {
                "id": risk.id,
                "name": risk.name,
                "color_hex": risk.color_hex,
            }
            if risk
            else None
        ),
        "risk_score": comment.risk_score,
        "pedagogical_categories": [
            {
                "id": link.pedagogical_category_rel.id,
                "name": link.pedagogical_category_rel.name,
                "description": link.pedagogical_category_rel.description,
                "color_hex": link.pedagogical_category_rel.color_hex,
                "score": link.score,
            }
            for link in comment.pedagogical_categories
            if link.pedagogical_category_rel
        ],
        "risk_level_modified_by_director": comment.risk_level_modified_by_director,
        "pedagogical_category_modified_by_director": (
            comment.pedagogical_category_modified_by_director
        ),
        "risk_level_ai_model": comment.risk_level_ai_model,
        "pedagogical_category_ai_model": comment.pedagogical_category_ai_model,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
