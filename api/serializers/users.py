"""Serializer for UserModel to dictionary representation."""

from api.models.user import UserModel


def user_to_dict(user: UserModel, roles: list[str] | None = None) -> dict:
    """Convert UserModel instance to dictionary."""

    return {
        "id": user.id,
        "uid": user.uid,
        "email": user.email,
        "username": user.username,
        "name": user.name,
        "department_id": user.department_id,
        "active": user.active,
        "avatar_url": user.avatar_url,
        "roles": roles or [],
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
