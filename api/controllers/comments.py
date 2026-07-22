"""
Comments controller
"""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.comments import get_comment_service
from api.schemas.comment import CommentFilters
from api.services.comment_service import CommentService


class CommentsController:
    """Comments controller"""

    def __init__(self, service: CommentService):
        self.service = service

    async def get_all(
        self,
        filters: CommentFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all comments based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, comment_id: int):
        """Get a comment by ID."""

        return await self.service.get_by_id(comment_id)

    async def count_by_department_and_period(
        self,
        department_id: int,
        academic_period_id: int,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ):
        """Count comments by department for current and previous academic period."""

        return await self.service.count_by_department_and_period(
            department_id,
            academic_period_id,
            risk_level,
            pedagogical_category_id,
            teacher_id,
        )


def get_comments_controller(
    service: CommentService = Depends(get_comment_service),
):
    """Get comments controller"""

    return CommentsController(service)
