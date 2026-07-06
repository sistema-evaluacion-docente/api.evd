"""
Comments repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.evaluation import EvaluationModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.serializers.comments import comment_to_dict


class CommentsRepository:
    """Comments repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        teacher_id: int | None,
        evaluation_id: int | None,
        academic_groups_id: int | None,
        original_text: str,
    ) -> dict:
        """Create a new comment."""

        comment = CommentModel(
            teacher_id=teacher_id,
            evaluation_id=evaluation_id,
            academic_groups_id=academic_groups_id,
            original_text=original_text,
            risk_level=None,
            pedagogical_category_id=None,
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)

        return comment_to_dict(comment)

    async def get_by_id(self, comment_id: int) -> dict | None:
        """Get a comment by ID."""

        comment = (
            self.db.query(CommentModel).filter(
                CommentModel.id == comment_id).first()
        )

        if not comment:
            return None

        return comment_to_dict(comment)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all comments for a given evaluation with teacher and course info."""

        results = (
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
            .filter(CommentModel.evaluation_id == evaluation_id)
            .all()
        )

        return [
            comment_to_dict(
                comment,
                group_name=group_name,
                teacher_name=teacher_name,
                teacher_avatar_url=teacher_avatar_url,
                course_name=course_name,
            )
            for comment, group_name, teacher_name, teacher_avatar_url, course_name in results
        ]

    async def get_by_evaluation_paginated(
        self,
        evaluation_id: int,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ) -> dict:
        """Get comments for a given evaluation with pagination and search."""

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
            .filter(CommentModel.evaluation_id == evaluation_id)
        )

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
                | (CourseModel.name.ilike(search_pattern))
            )

        total = base_query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        results = (
            base_query.order_by(CommentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "comments": [
                comment_to_dict(
                    comment,
                    group_name=group_name,
                    teacher_name=teacher_name,
                    teacher_avatar_url=teacher_avatar_url,
                    course_name=course_name,
                )
                for comment, group_name, teacher_name, teacher_avatar_url, course_name in results
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_teacher(self, teacher_id: int) -> list[dict]:
        """Get all comments for a given teacher across all evaluations."""

        comments = (
            self.db.query(CommentModel)
            .filter(CommentModel.teacher_id == teacher_id)
            .order_by(CommentModel.created_at.desc())
            .all()
        )

        return [comment_to_dict(c) for c in comments]

    async def count_by_department_and_period(
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
                CommentModel.pedagogical_category_id == pedagogical_category_id)
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
                    CommentModel.pedagogical_category_id == pedagogical_category_id)
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

    async def get_by_academic_group(self, academic_groups_id: int) -> list[dict]:
        """Get all comments for a given academic group."""

        comments = (
            self.db.query(CommentModel)
            .filter(CommentModel.academic_groups_id == academic_groups_id)
            .all()
        )

        return [comment_to_dict(c) for c in comments]

    async def get_by_period(
        self,
        academic_period_id: int,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ) -> dict | None:
        """Get comments for a specific academic period with pagination and optional filters."""

        from api.models.academic_period import AcademicPeriodModel
        from api.models.teacher import TeacherModel
        from api.models.user import UserModel

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        if not period:
            return None

        base_query = (
            self.db.query(CommentModel)
            .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
            .filter(EvaluationModel.academic_period_id == academic_period_id)
        )

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(
                TeacherModel, CommentModel.teacher_id == TeacherModel.id
            ).outerjoin(UserModel, TeacherModel.user_id == UserModel.id).filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
            )

        if risk_level is not None:
            base_query = base_query.filter(
                CommentModel.risk_level == risk_level)

        if pedagogical_category_id is not None:
            base_query = base_query.filter(
                CommentModel.pedagogical_category_id == pedagogical_category_id
            )

        if teacher_id is not None:
            base_query = base_query.filter(
                CommentModel.teacher_id == teacher_id)

        total = base_query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        comments = (
            base_query.order_by(CommentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "period_id": academic_period_id,
            "period_code": period.code,
            "period_name": period.name,
            "comment_count": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "comments": [comment_to_dict(c) for c in comments],
        }


def get_comments_repository(db: Annotated[Session, Depends(get_db)]):
    """Get comments repository"""

    return CommentsRepository(db)
