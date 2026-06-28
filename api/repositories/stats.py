"""
Stats repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_period import AcademicPeriodModel
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_score import EvaluationScoreModel


class StatsRepository:
    """Stats repository"""

    def __init__(self, db: Session):
        self.db = db

    async def get_department_averages_by_period(
        self, department_id: int | None = None
    ) -> list[dict]:
        """
        Get global average per department per academic period.

        Joins evaluations -> evaluation_scores and groups by
        (department, academic_period).
        """

        query = (
            self.db.query(
                DepartmentModel.id.label("department_id"),
                DepartmentModel.name.label("department_name"),
                DepartmentModel.code.label("department_code"),
                AcademicPeriodModel.id.label("academic_period_id"),
                AcademicPeriodModel.code.label("academic_period_code"),
                AcademicPeriodModel.name.label("academic_period_name"),
                func.avg(EvaluationScoreModel.overall_average).label("global_average"),
                func.sum(EvaluationScoreModel.respondent_count).label(
                    "total_respondents"
                ),
                func.count(EvaluationScoreModel.id).label("evaluation_count"),
            )
            .join(
                EvaluationModel,
                EvaluationModel.department_id == DepartmentModel.id,
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .join(
                AcademicPeriodModel,
                AcademicPeriodModel.id == EvaluationModel.academic_period_id,
            )
            .group_by(
                DepartmentModel.id,
                DepartmentModel.name,
                DepartmentModel.code,
                AcademicPeriodModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .order_by(
                AcademicPeriodModel.code.desc(),
                DepartmentModel.name,
            )
        )

        if department_id is not None:
            query = query.filter(DepartmentModel.id == department_id)

        results = query.all()

        return [
            {
                "department_id": row.department_id,
                "department_name": row.department_name,
                "department_code": row.department_code,
                "academic_period_id": row.academic_period_id,
                "academic_period_code": row.academic_period_code,
                "academic_period_name": row.academic_period_name,
                "global_average": float(row.global_average)
                if row.global_average
                else None,
                "total_respondents": row.total_respondents,
                "evaluation_count": row.evaluation_count,
            }
            for row in results
        ]


def get_stats_repository(db: Annotated[Session, Depends(get_db)]):
    """Get stats repository"""

    return StatsRepository(db)
