"""
Comments repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.comment import CommentModel
from api.models.evaluation import EvaluationModel
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
            self.db.query(CommentModel).filter(CommentModel.id == comment_id).first()
        )

        if not comment:
            return None

        return comment_to_dict(comment)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all comments for a given evaluation."""

        comments = (
            self.db.query(CommentModel)
            .filter(CommentModel.evaluation_id == evaluation_id)
            .all()
        )

        return [comment_to_dict(c) for c in comments]

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
    ) -> dict:
        """Count comments by department for current and previous academic period."""

        current_count = (
            self.db.query(CommentModel)
            .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
            .filter(
                EvaluationModel.department_id == department_id,
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .count()
        )

        previous_count = None
        if previous_period_id:
            previous_count = (
                self.db.query(CommentModel)
                .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
                .filter(
                    EvaluationModel.department_id == department_id,
                    EvaluationModel.academic_period_id == previous_period_id,
                )
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


def get_comments_repository(db: Annotated[Session, Depends(get_db)]):
    """Get comments repository"""

    return CommentsRepository(db)
