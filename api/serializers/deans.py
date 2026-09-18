"""Serializer for DeanModel to dictionary representation."""

from api.models.dean import DeanModel


def dean_to_dict(dean: DeanModel) -> dict:
    """Convert DeanModel instance to dictionary."""

    return {
        "id": dean.id,
        "user_id": dean.user_id,
        "faculty_id": dean.faculty_id,
        "active": dean.active,
        "created_at": dean.created_at,
        "updated_at": dean.updated_at,
    }
