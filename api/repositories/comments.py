"""
Comments repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.evaluation import EvaluationModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.comment import CommentFilters
from api.serializers.comments import comment_to_dict


class CommentsRepository(BaseRepository[CommentModel]):
    """Comments repository"""

    def __init__(self, db: Session):
        super().__init__(CommentModel, db)

    def search(
        self,
        filters: CommentFilters,
        pagination: PaginationParams,
    ) -> tuple[list[dict], int]:
        """Search comments with filters and pagination."""

        base_query = (
            self.db.query(
                CommentModel,
                AcademicGroupModel.group_name,
                UserModel.name.label("teacher_name"),
                UserModel.avatar_url.label("teacher_avatar_url"),
                CourseModel.name.label("course_name"),
            )
            .outerjoin(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            )
            .outerjoin(
                TeacherModel,
                CommentModel.teacher_id == TeacherModel.id,
            )
            .outerjoin(
                UserModel,
                TeacherModel.user_id == UserModel.id,
            )
            .outerjoin(
                CourseModel,
                AcademicGroupModel.course_id == CourseModel.id,
            )
        )

        if filters.evaluation_id is not None:
            base_query = base_query.filter(
                CommentModel.evaluation_id == filters.evaluation_id
            )

        if filters.teacher_id is not None:
            base_query = base_query.filter(
                CommentModel.teacher_id == filters.teacher_id
            )

        if filters.academic_groups_id is not None:
            base_query = base_query.filter(
                CommentModel.academic_groups_id == filters.academic_groups_id
            )

        if filters.academic_period_id is not None:
            base_query = base_query.join(
                EvaluationModel,
                CommentModel.evaluation_id == EvaluationModel.id,
            ).filter(EvaluationModel.academic_period_id == filters.academic_period_id)

        if filters.risk_level is not None:
            base_query = base_query.filter(
                CommentModel.risk_level == filters.risk_level
            )

        if filters.pedagogical_category_id is not None:
            base_query = base_query.filter(
                CommentModel.pedagogical_category_id == filters.pedagogical_category_id
            )

        if filters.search:
            search_pattern = f"%{filters.search}%"
            base_query = base_query.filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
                | (CourseModel.name.ilike(search_pattern))
            )

        total = base_query.count()

        results = (
            base_query.order_by(CommentModel.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
            .all()
        )

        items = [
            comment_to_dict(
                comment,
                group_name=group_name,
                teacher_name=teacher_name,
                teacher_avatar_url=teacher_avatar_url,
                course_name=course_name,
            )
            for comment, group_name, teacher_name, teacher_avatar_url, course_name in results
        ]

        return items, total

    def get_by_id_enriched(self, comment_id: int) -> dict | None:
        """Get a comment by ID with enriched teacher/course info."""

        result = (
            self.db.query(
                CommentModel,
                AcademicGroupModel.group_name,
                UserModel.name.label("teacher_name"),
                UserModel.avatar_url.label("teacher_avatar_url"),
                CourseModel.name.label("course_name"),
            )
            .outerjoin(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            )
            .outerjoin(
                TeacherModel,
                CommentModel.teacher_id == TeacherModel.id,
            )
            .outerjoin(
                UserModel,
                TeacherModel.user_id == UserModel.id,
            )
            .outerjoin(
                CourseModel,
                AcademicGroupModel.course_id == CourseModel.id,
            )
            .filter(CommentModel.id == comment_id)
            .first()
        )

        if not result:
            return None

        comment, group_name, teacher_name, teacher_avatar_url, course_name = result

        return comment_to_dict(
            comment,
            group_name=group_name,
            teacher_name=teacher_name,
            teacher_avatar_url=teacher_avatar_url,
            course_name=course_name,
        )

    def count_by_department_and_period(
        self,
        department_id: int,
        academic_period_id: int,
        previous_period_id: int | None = None,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ) -> dict:
        """Count comments by department for current and previous academic period."""

        base_filters = [
            EvaluationModel.department_id == department_id,
            EvaluationModel.academic_period_id == academic_period_id,
        ]

        if risk_level is not None:
            base_filters.append(CommentModel.risk_level == risk_level)
        if pedagogical_category_id is not None:
            base_filters.append(
                CommentModel.pedagogical_category_id == pedagogical_category_id
            )
        if teacher_id is not None:
            base_filters.append(CommentModel.teacher_id == teacher_id)

        current_count = (
            self.db.query(CommentModel)
            .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
            .filter(*base_filters)
            .count()
        )

        previous_count = None
        if previous_period_id:
            prev_filters = [
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id == previous_period_id,
            ]
            if risk_level is not None:
                prev_filters.append(CommentModel.risk_level == risk_level)
            if pedagogical_category_id is not None:
                prev_filters.append(
                    CommentModel.pedagogical_category_id == pedagogical_category_id
                )
            if teacher_id is not None:
                prev_filters.append(CommentModel.teacher_id == teacher_id)

            previous_count = (
                self.db.query(CommentModel)
                .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
                .filter(*prev_filters)
                .count()
            )

        return {
            "current_count": current_count,
            "previous_count": previous_count,
        }


def get_comments_repository(db: Annotated[Session, Depends(get_db)]):
    """Get comments repository"""

    return CommentsRepository(db)
