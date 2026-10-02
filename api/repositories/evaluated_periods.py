"""
Academic periods a department actually has evaluations for.
"""

from sqlalchemy.orm import Session

from api.models.academic_period import AcademicPeriodModel
from api.models.evaluation import EvaluationModel


def query_evaluated_periods(db: Session, department_id: int) -> list[dict]:
    """Periods whose grades are already loaded for the department, newest
    first.

    `/academic-periods` is the institution-wide catalogue: it lists every
    period anyone created, including the current one, whose grades usually
    arrive at the start of the next. Anything that only makes sense where a
    department has data — a plan's origin period, the department summary —
    should offer these instead."""

    rows = (
        db.query(
            AcademicPeriodModel.id,
            AcademicPeriodModel.code,
            AcademicPeriodModel.name,
        )
        .join(
            EvaluationModel,
            EvaluationModel.academic_period_id == AcademicPeriodModel.id,
        )
        .filter(
            EvaluationModel.department_id == department_id,
            EvaluationModel.status == "COMPLETED",
            EvaluationModel.active.is_(True),
        )
        .distinct()
        .order_by(AcademicPeriodModel.code.desc())
        .all()
    )

    return [{"id": row.id, "code": row.code, "name": row.name} for row in rows]
