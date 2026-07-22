"""Repository for academic group-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.repositories.base import BaseRepository
from api.schemas.academic_group import AcademicGroupFilters


class AcademicGroupsRepository(BaseRepository[AcademicGroupModel]):
    """Repository for academic group-related database operations."""

    def __init__(self, db: Session):
        super().__init__(AcademicGroupModel, db)

    @staticmethod
    def _eager_options():
        """Eager-load course, teacher (with user) and period to avoid N+1 queries."""

        return (
            joinedload(AcademicGroupModel.course),
            joinedload(AcademicGroupModel.teacher).joinedload(TeacherModel.user),
            joinedload(AcademicGroupModel.academic_period),
        )

    def get_by_id(self, group_id: int) -> AcademicGroupModel | None:
        """Get an academic group by ID with its relationships loaded."""

        return (
            self.db.query(AcademicGroupModel)
            .options(*self._eager_options())
            .filter(AcademicGroupModel.id == group_id)
            .first()
        )

    def search(
        self,
        filters: AcademicGroupFilters,
        pagination: PaginationParams,
    ) -> tuple[list[AcademicGroupModel], int]:
        """Search for academic groups based on filters and pagination parameters."""

        query = self.db.query(AcademicGroupModel).options(*self._eager_options())

        search_term = filters.search.strip() if filters.search else ""
        needs_course_join = bool(search_term) or filters.department_id is not None

        if needs_course_join:
            query = query.join(
                CourseModel, AcademicGroupModel.course_id == CourseModel.id
            )

        if search_term:
            like_term = f"%{search_term}%"

            query = query.filter(
                or_(
                    AcademicGroupModel.group_name.ilike(like_term),
                    CourseModel.code.ilike(like_term),
                    CourseModel.name.ilike(like_term),
                )
            )

        if filters.course_id is not None:
            query = query.filter(AcademicGroupModel.course_id == filters.course_id)

        if filters.teacher_id is not None:
            query = query.filter(AcademicGroupModel.teacher_id == filters.teacher_id)

        if filters.academic_period_id is not None:
            query = query.filter(
                AcademicGroupModel.academic_period_id == filters.academic_period_id
            )

        if filters.department_id is not None:
            query = query.filter(CourseModel.department_id == filters.department_id)

        query = query.order_by(AcademicGroupModel.created_at.desc())

        return self.paginate(query, pagination)

    def get_by_course_teacher_period_name(
        self,
        course_id: int,
        teacher_id: int,
        academic_period_id: int,
        group_name: str | None,
        exclude_id: int | None = None,
    ) -> AcademicGroupModel | None:
        """Get a group by the unique (course, teacher, period, group_name) combination."""

        query = self.db.query(AcademicGroupModel).filter(
            AcademicGroupModel.course_id == course_id,
            AcademicGroupModel.teacher_id == teacher_id,
            AcademicGroupModel.academic_period_id == academic_period_id,
        )

        if group_name is None:
            query = query.filter(AcademicGroupModel.group_name.is_(None))
        else:
            query = query.filter(AcademicGroupModel.group_name == group_name)

        if exclude_id is not None:
            query = query.filter(AcademicGroupModel.id != exclude_id)

        return query.first()

    def get_by_teacher_and_period(
        self, teacher_id: int, academic_period_id: int
    ) -> list[AcademicGroupModel]:
        """Get all groups for a teacher in a given period."""

        return (
            self.db.query(AcademicGroupModel)
            .options(*self._eager_options())
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                AcademicGroupModel.academic_period_id == academic_period_id,
            )
            .all()
        )

    def count_evaluation_scores(self, group_id: int) -> int:
        """Count evaluation scores associated with an academic group."""

        return (
            self.db.query(EvaluationScoreModel)
            .filter(EvaluationScoreModel.academic_group_id == group_id)
            .count()
        )

    def count_comments(self, group_id: int) -> int:
        """Count comments associated with an academic group."""

        return (
            self.db.query(CommentModel)
            .filter(CommentModel.academic_groups_id == group_id)
            .count()
        )

    def update_group(self, group: AcademicGroupModel, data: dict) -> AcademicGroupModel:
        """Update an academic group's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(group, field, value)

        self.db.commit()
        self.db.refresh(group)

        return group

    def delete_group(self, group_id: int) -> AcademicGroupModel | None:
        """Delete an academic group by ID."""

        group = self.get(group_id)

        if not group:
            return None

        self.db.delete(group)
        self.db.commit()

        return group


def get_academic_groups_repository(
    db: Annotated[Session, Depends(get_db)],
) -> AcademicGroupsRepository:
    """Dependency injection for AcademicGroupsRepository."""

    return AcademicGroupsRepository(db)
