"""Serializer for DepartmentModel to dictionary representation."""

from api.models.department import DepartmentModel


def department_to_dict(department: DepartmentModel) -> dict:
    """Convert DepartmentModel instance to dictionary."""

    return {
        "id": department.id,
        "code": department.code,
        "name": department.name,
        "faculty_id": department.faculty_id,
        "active": department.active,
        "created_at": department.created_at,
        "updated_at": department.updated_at,
    }
