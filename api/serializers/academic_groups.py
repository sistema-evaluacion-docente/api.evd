"""Serializer for AcademicGroupModel to dictionary representation."""

from api.models.academic_group import AcademicGroupModel


def academic_group_to_dict(group: AcademicGroupModel) -> dict:
    """Convert AcademicGroupModel instance to dictionary."""

    return {
        "id": group.id,
        "course_id": group.course_id,
        "teacher_id": group.teacher_id,
        "academic_period_id": group.academic_period_id,
        "group_name": group.group_name,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }
