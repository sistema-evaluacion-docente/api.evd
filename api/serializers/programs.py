"""Serializer for ProgramModel to dictionary representation."""

from api.models.program import ProgramModel


def program_to_dict(program: ProgramModel) -> dict:
    """Convert ProgramModel instance to dictionary."""

    return {
        "id": program.id,
        "name": program.name,
        "code": program.code,
        "active": program.active,
        "created_at": program.created_at,
        "updated_at": program.updated_at,
    }
