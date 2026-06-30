"""
Teachers repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.schemas.teacher import TeacherCreate, TeacherUpdate
from api.serializers.teachers import teacher_to_dict


class TeachersRepository:
    """Teachers repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: TeacherCreate) -> dict:
        """Create a new teacher."""

        teacher = TeacherModel(
            institutional_code=data.institutional_code,
            department_id=data.department_id,
            contract_type=data.contract_type,
            user_id=data.user_id,
            active=data.active,
        )

        self.db.add(teacher)
        self.db.commit()
        self.db.refresh(teacher)

        return teacher_to_dict(teacher)

    async def get_all(self) -> list[dict]:
        """Get all teachers ordered by creation date descending."""

        teachers = (
            self.db.query(TeacherModel).order_by(TeacherModel.created_at.desc()).all()
        )

        return [teacher_to_dict(t) for t in teachers]

    async def get_by_id(self, teacher_id: int) -> dict | None:
        """Get a teacher by ID."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        return teacher_to_dict(teacher)

    async def get_by_institutional_code(self, institutional_code: str) -> dict | None:
        """Get a teacher by institutional code."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code == institutional_code)
            .first()
        )

        if not teacher:
            return None

        return teacher_to_dict(teacher)

    async def get_by_institutional_codes(self, codes: list[str]) -> list[dict]:
        """Get existing teachers by a list of institutional codes."""

        teachers = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code.in_(codes))
            .all()
        )

        return [teacher_to_dict(t) for t in teachers]

    async def update(self, teacher_id: int, data: TeacherUpdate) -> dict | None:
        """Update a teacher's fields."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(teacher, field, value)

        self.db.commit()
        self.db.refresh(teacher)

        return teacher_to_dict(teacher)


    async def get_history(self, teacher_id: int) -> dict | None:
        """Return the teacher's average score for each academic period."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not teacher:
            return None

        teacher_user = (
            self.db.query(UserModel).filter(UserModel.id == teacher.user_id).first()
            if teacher.user_id
            else None
        )

        rows = (
            self.db.query(
                EvaluationModel.id.label("evaluation_id"),
                AcademicPeriodModel.code.label("period_code"),
                AcademicPeriodModel.name.label("period_name"),
                func.avg(EvaluationScoreModel.overall_average).label("avg_score"),
                func.count(EvaluationScoreModel.id).label("group_count"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                AcademicPeriodModel,
                EvaluationModel.academic_period_id == AcademicPeriodModel.id,
            )
            .filter(AcademicGroupModel.teacher_id == teacher_id)
            .group_by(
                EvaluationModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
            )
            .order_by(AcademicPeriodModel.code.asc())
            .all()
        )

        return {
            "teacher_id": teacher_id,
            "institutional_code": teacher.institutional_code,
            "name": teacher_user.name if teacher_user else None,
            "history": [
                {
                    "evaluation_id": row.evaluation_id,
                    "period_code": row.period_code,
                    "period_name": row.period_name,
                    "overall_average": (
                        float(row.avg_score) if row.avg_score else None
                    ),
                    "group_count": row.group_count,
                }
                for row in rows
            ],
        }


def get_teachers_repository(db: Annotated[Session, Depends(get_db)]):
    """Get teachers repository"""

    return TeachersRepository(db)
