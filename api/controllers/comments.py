"""
Comments controller
"""

from fastapi.param_functions import Depends

from api.repositories.comments import CommentsRepository, get_comments_repository


class CommentsController:
    """Comments controller"""

    def __init__(self, repository: CommentsRepository):
        self.repository = repository

    async def get_by_id(self, comment_id: int) -> dict | None:
        """Get a comment by ID."""

        return await self.repository.get_by_id(comment_id)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all comments for a given evaluation."""

        return await self.repository.get_by_evaluation(evaluation_id)

    async def get_by_teacher(self, teacher_id: int) -> list[dict]:
        """Get all comments for a given teacher."""

        return await self.repository.get_by_teacher(teacher_id)

    async def get_by_academic_group(self, academic_groups_id: int) -> list[dict]:
        """Get all comments for a given academic group."""

        return await self.repository.get_by_academic_group(academic_groups_id)


def get_comments_controller(
    repository: CommentsRepository = Depends(get_comments_repository),
):
    """Get comments controller"""

    return CommentsController(repository)
