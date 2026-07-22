"""Serializer for TeacherModel to dictionary representation."""

from api.models.teacher import TeacherModel


def teacher_to_dict(teacher: TeacherModel) -> dict:
    """Convert TeacherModel instance to dictionary."""

    return {
        "id": teacher.id,
        "institutional_code": teacher.user.institutional_code if teacher.user else None,
        "department_id": teacher.department_id,
        "contract_type": teacher.contract_type,
        "user_id": teacher.user_id,
        "active": teacher.active,
        "created_at": teacher.created_at,
        "updated_at": teacher.updated_at,
    }
