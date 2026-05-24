"""Serializer for UserModel to dictionary representation."""

from api.models.user import UserModel


def user_to_dict(user: UserModel) -> dict:
    """Convert UserModel instance to dictionary."""

    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
        "username": user.username,
        "photo_url": user.photo_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
