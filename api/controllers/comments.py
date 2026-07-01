"""
Comments controller
"""

from fastapi.param_functions import Depends

from api.repositories.academic_periods import (
    AcademicPeriodsRepository,
    get_academic_periods_repository,
)
from api.repositories.comments import CommentsRepository, get_comments_repository


class CommentsController:
    """Comments controller"""

    def __init__(
        self,
        repository: CommentsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
    ):
        self.repository = repository
        self.academic_periods_repository = academic_periods_repository

    async def get_by_id(self, comment_id: int) -> dict | None:
        """Get a comment by ID."""

        return await self.repository.get_by_id(comment_id)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all comments for a given evaluation."""

        return await self.repository.get_by_evaluation(evaluation_id)

    async def get_by_teacher(self, teacher_id: int) -> list[dict]:
        """Get all comments for a given teacher."""

        return await self.repository.get_by_teacher(teacher_id)

    async def count_by_department_and_period(
        self,
        department_id: int,
        academic_period_id: int,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ) -> dict:
        """Count comments by department for current and previous academic period."""

        period = await self.academic_periods_repository.get_by_id(academic_period_id)

        previous_period_id = None

        if period:
            prev_code = await self.academic_periods_repository.get_previous_period_code(
                period["code"]
            )

            if prev_code:
                prev_period = await self.academic_periods_repository.get_by_code(
                    prev_code
                )

                if prev_period:
                    previous_period_id = prev_period["id"]

        return await self.repository.count_by_department_and_period(
            department_id,
            academic_period_id,
            previous_period_id,
            risk_level,
            pedagogical_category_id,
            teacher_id,
        )

    async def get_by_academic_group(self, academic_groups_id: int) -> list[dict]:
        """Get all comments for a given academic group."""

        return await self.repository.get_by_academic_group(academic_groups_id)


def get_comments_controller(
    repository: CommentsRepository = Depends(get_comments_repository),
    academic_periods_repository: AcademicPeriodsRepository = Depends(
        get_academic_periods_repository
    ),
):
    """Get comments controller"""

    return CommentsController(repository, academic_periods_repository)
