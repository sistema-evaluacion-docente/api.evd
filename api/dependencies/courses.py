"""Dependency injection for course-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.courses import CoursesRepository, get_courses_repository
from api.services.audit_service import AuditService
from api.services.course_service import CourseService


def get_course_service(
    courses_repository: CoursesRepository = Depends(get_courses_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> CourseService:
    """Dependency injection for CourseService."""

    return CourseService(courses_repository, audit_service)
