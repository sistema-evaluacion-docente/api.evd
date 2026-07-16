"""Serializer for DirectorsModel to dictionary representation."""

from api.models.director import DirectorsModel


def director_to_dict(director: DirectorsModel) -> dict:
    """Convert DirectorsModel instance to dictionary."""

    return {
        "id": director.id,
        "user_id": director.user_id,
        "department_id": director.department_id,
        "active": director.active,
        "created_at": director.created_at,
        "updated_at": director.updated_at,
    }
