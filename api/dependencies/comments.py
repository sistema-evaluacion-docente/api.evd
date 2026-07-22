"""Dependency injection for comment-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.comments import CommentsRepository, get_comments_repository
from api.services.audit_service import AuditService
from api.services.comment_service import CommentService


def get_comment_service(
    comments_repository: CommentsRepository = Depends(get_comments_repository),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> CommentService:
    """Dependency injection for CommentService."""

    return CommentService(
        comments_repository,
        academic_periods_repository,
        audit_service,
    )
