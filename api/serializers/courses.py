"""Serializer for CourseModel to dictionary representation."""

from api.models.course import CourseModel


def course_to_dict(course: CourseModel) -> dict:
    """Convert CourseModel instance to dictionary."""

    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "department_id": course.department_id,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
    }
