"""Serializer for UserModel to dictionary representation."""

from api.models.user import UserModel


def user_to_dict(
    user: UserModel, roles: list[str] | None = None, department_id: int | None = None
) -> dict:
    """Convert UserModel instance to dictionary."""

    return {
        "id": user.id,
        "uid": user.uid,
        "email": user.email,
        "department_id": department_id,
        "name": user.name,
        "active": user.active,
        "avatar_url": user.avatar_url,
        "roles": roles or [],
        "teacher_id": user.teacher.id if user.teacher else None,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
