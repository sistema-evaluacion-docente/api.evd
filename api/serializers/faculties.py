"""Serializer for FacultyModel to dictionary representation."""

from api.models.faculty import FacultyModel


def faculty_to_dict(faculty: FacultyModel) -> dict:
    """Convert FacultyModel instance to dictionary."""

    return {
        "id": faculty.id,
        "name": faculty.name,
        "code": faculty.code,
        "active": faculty.active,
        "created_at": faculty.created_at,
        "updated_at": faculty.updated_at,
    }
