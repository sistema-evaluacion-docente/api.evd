"""Service for comment-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.comments import CommentsRepository
from api.repositories.pedagogical_categories import PedagogicalCategoriesRepository
from api.repositories.risk_levels import RiskLevelsRepository
from api.schemas.comment import CommentFilters, CommentUpdate
from api.schemas.pagination import build_paginated_response
from api.services.audit_service import AuditService


class CommentService:
    """Service for comment-related business operations."""

    def __init__(
        self,
        comments_repository: CommentsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
        risk_levels_repository: RiskLevelsRepository,
        pedagogical_categories_repository: PedagogicalCategoriesRepository,
        audit_service: AuditService,
    ):
        self.comments_repository = comments_repository
        self.academic_periods_repository = academic_periods_repository
        self.risk_levels_repository = risk_levels_repository
        self.pedagogical_categories_repository = pedagogical_categories_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: CommentFilters,
        pagination: PaginationParams,
        department_id: int | None = None,
    ) -> dict:
        """Retrieve all comments based on filters and pagination."""

        items, total = self.comments_repository.search(filters, pagination, department_id)

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

    async def update_classification(
        self,
        comment_id: int,
        data: CommentUpdate,
        current_user: dict,
    ) -> dict | None:
        """Update a comment's risk_level and/or pedagogical categories.

        Only the director of the department that owns the comment's evaluation
        may perform this update. Returns None when the comment doesn't exist
        (or has no department to authorize against), which the route maps to 404.
        """

        department_id = self.comments_repository.get_department_id(comment_id)

        if department_id is None:
            return None

        if department_id != current_user.get("department_id"):
            raise PermissionDeniedError(
                "Solo el director del departamento asociado puede modificar este comentario"
            )

        if data.risk_level is not None:
            risk = await self.risk_levels_repository.get_by_id(data.risk_level)

            if not risk:
                raise ResourceNotFoundError("Nivel de riesgo", data.risk_level)

        if data.pedagogical_category_ids is not None:
            for category_id in data.pedagogical_category_ids:
                category = await self.pedagogical_categories_repository.get_by_id(
                    category_id
                )

                if not category:
                    raise ResourceNotFoundError("Categoría pedagógica", category_id)

        updated = self.comments_repository.update_classification(
            comment_id,
            risk_level=data.risk_level,
            pedagogical_category_ids=data.pedagogical_category_ids,
        )

        if not updated:
            return None

        await self.audit_service.log(
            action="UPDATE",
            entity_name="comments",
            entity_id=comment_id,
            actor_id=current_user.get("id"),
            description=f"El director modificó la clasificación del comentario {comment_id}",
        )

        return self.comments_repository.get_by_id_enriched(comment_id)
