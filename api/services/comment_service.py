"""Service for comment-related business operations."""

from api.core.pagination import PaginationParams
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.comments import CommentsRepository
from api.schemas.comment import CommentFilters
from api.schemas.pagination import build_paginated_response
from api.services.audit_service import AuditService


class CommentService:
    """Service for comment-related business operations."""

    def __init__(
        self,
        comments_repository: CommentsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
        audit_service: AuditService,
    ):
        self.comments_repository = comments_repository
        self.academic_periods_repository = academic_periods_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: CommentFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all comments based on filters and pagination."""

        items, total = self.comments_repository.search(filters, pagination)

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, comment_id: int) -> dict | None:
        """Retrieve a comment by ID with enriched info."""

        return self.comments_repository.get_by_id_enriched(comment_id)

    async def count_by_department_and_period(
        self,
        department_id: int,
        academic_period_id: int,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ) -> dict:
        """Count comments by department for current and previous academic period."""

        period = self.academic_periods_repository.get(academic_period_id)

        previous_period_id = None

        if period:
            prev_code = self.academic_periods_repository.get_previous_period_code(
                period.code
            )

            if prev_code:
                prev_period = self.academic_periods_repository.get_by_code(prev_code)

                if prev_period:
                    previous_period_id = prev_period.id

        return self.comments_repository.count_by_department_and_period(
            department_id,
            academic_period_id,
            previous_period_id,
            risk_level,
            pedagogical_category_id,
            teacher_id,
        )
