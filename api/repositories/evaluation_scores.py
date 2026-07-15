"""
Evaluation scores repository
"""

from decimal import Decimal
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.course import CourseModel
from api.models.evaluation_score import EvaluationScoreModel
from api.serializers.evaluation_scores import evaluation_score_to_dict


class EvaluationScoresRepository:
    """Evaluation scores repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        evaluation_id: int,
        academic_group_id: int,
        respondent_count: int,
        overall_average: Decimal | None = None,
    ) -> dict:
        """Create a new evaluation score."""

        score = EvaluationScoreModel(
            evaluation_id=evaluation_id,
            academic_group_id=academic_group_id,
            respondent_count=respondent_count,
            overall_average=overall_average,
        )

        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)

        return evaluation_score_to_dict(score)

    async def get_all(self) -> list[dict]:
        """Get all evaluation scores."""

        scores = (
            self.db.query(EvaluationScoreModel)
            .order_by(EvaluationScoreModel.created_at.desc())
            .all()
        )

        return [evaluation_score_to_dict(s) for s in scores]

    async def get_by_id(self, score_id: int) -> dict | None:
        """Get an evaluation score by ID."""

        result = (
            self.db.query(
                EvaluationScoreModel,
                AcademicGroupModel.group_name,
                CourseModel.name.label("course_name"),
                CourseModel.code.label("course_code"),
            )
            .outerjoin(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .outerjoin(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(EvaluationScoreModel.id == score_id)
            .first()
        )

        if not result:
            return None

        score, group_name, course_name, course_code = result
        return evaluation_score_to_dict(score, group_name, course_name, course_code)

    async def get_by_evaluation(self, evaluation_id: int) -> list[dict]:
        """Get all scores for a given evaluation, including group_name and course_name."""

        results = (
            self.db.query(
                EvaluationScoreModel,
                AcademicGroupModel.group_name,
                CourseModel.name.label("course_name"),
                CourseModel.code.label("course_code"),
            )
            .outerjoin(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .outerjoin(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .all()
        )

        return [
            evaluation_score_to_dict(score, group_name, course_name, course_code)
            for score, group_name, course_name, course_code in results
        ]

    async def get_by_evaluation_paginated(
        self,
        evaluation_id: int,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ) -> dict:
        """Get scores for a given evaluation with pagination and search."""

        base_query = (
            self.db.query(
                EvaluationScoreModel,
                AcademicGroupModel.group_name,
                CourseModel.name.label("course_name"),
                CourseModel.code.label("course_code"),
            )
            .outerjoin(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .outerjoin(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
        )

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.filter(
                AcademicGroupModel.group_name.ilike(search_pattern)
                | CourseModel.name.ilike(search_pattern)
            )

        total = base_query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        results = (
            base_query.order_by(EvaluationScoreModel.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "scores": [
                evaluation_score_to_dict(score, group_name, course_name, course_code)
                for score, group_name, course_name, course_code in results
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_evaluation_and_group(
        self, evaluation_id: int, academic_group_id: int
    ) -> dict | None:
        """Get a score by evaluation and academic group — used for duplicate detection."""

        score = (
            self.db.query(EvaluationScoreModel)
            .filter(
                EvaluationScoreModel.evaluation_id == evaluation_id,
                EvaluationScoreModel.academic_group_id == academic_group_id,
            )
            .first()
        )

        if not score:
            return None

        return evaluation_score_to_dict(score)


def get_evaluation_scores_repository(db: Annotated[Session, Depends(get_db)]):
    """Get evaluation scores repository"""

    return EvaluationScoresRepository(db)
