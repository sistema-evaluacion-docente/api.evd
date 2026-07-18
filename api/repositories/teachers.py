"""Repository for teacher-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.teacher import TeacherFilters


class TeachersRepository(BaseRepository[TeacherModel]):
    """Repository for teacher-related database operations."""

    def __init__(self, db: Session):
        super().__init__(TeacherModel, db)

    def get_by_id(self, teacher_id: int) -> TeacherModel | None:
        """Get a teacher by ID with user relationship loaded."""

        return (
            self.db.query(TeacherModel)
            .options(joinedload(TeacherModel.user))
            .filter(TeacherModel.id == teacher_id)
            .first()
        )

    def get_by_institutional_code(self, institutional_code: str) -> TeacherModel | None:
        """Get a teacher by institutional code."""

        return (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code == institutional_code)
            .first()
        )

    def get_by_institutional_codes(self, codes: list[str]) -> list[TeacherModel]:
        """Get existing teachers by a list of institutional codes."""

        if not codes:
            return []

        return (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code.in_(codes))
            .all()
        )

    def search(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
    ) -> tuple[list[TeacherModel], int]:
        """Search for teachers based on filters and pagination parameters."""

        query = self.db.query(TeacherModel).options(joinedload(TeacherModel.user))

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        TeacherModel.institutional_code.ilike(like_term),
                        TeacherModel.contract_type.ilike(like_term),
                        UserModel.name.ilike(like_term),
                        UserModel.email.ilike(like_term),
                    )
                )

        if filters.active is not None:
            query = query.filter(TeacherModel.active == filters.active)

        if filters.department_id is not None:
            query = query.filter(TeacherModel.department_id == filters.department_id)

        if filters.contract_type is not None:
            query = query.filter(TeacherModel.contract_type == filters.contract_type)

        query = query.order_by(TeacherModel.created_at.desc())

        return self.paginate(query, pagination)

    def delete_teacher(self, teacher_id: int) -> TeacherModel | None:
        """Delete a teacher by ID. Raises ValueError if teacher has academic groups."""

        teacher = self.get_by_id(teacher_id)

        if not teacher:
            return None

        self.db.delete(teacher)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "No se puede eliminar el profesor porque tiene grupos académicos asociados"
            )

        return teacher

    def update_teacher(self, teacher: TeacherModel, data: dict) -> TeacherModel:
        """Update a teacher's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(teacher, field, value)

        self.db.commit()
        self.db.refresh(teacher)

        return teacher

    def get_teacher_averages_by_period(
        self, teacher_ids: list[int], academic_period_id: int
    ) -> dict[int, float]:
        """Get average evaluation scores for teachers in a given academic period."""

        if not teacher_ids:
            return {}

        avg_query = (
            self.db.query(
                AcademicGroupModel.teacher_id,
                func.avg(EvaluationScoreModel.overall_average).label("avg"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .filter(
                AcademicGroupModel.teacher_id.in_(teacher_ids),
                EvaluationModel.academic_period_id == academic_period_id,
            )
            .group_by(AcademicGroupModel.teacher_id)
        )

        return {row.teacher_id: float(row.avg) for row in avg_query.all()}

    def count_by_department(
        self,
        department_id: int,
        academic_period_id: int,
        previous_period_id: int | None = None,
    ) -> dict:
        """Count teachers by department for current and previous academic period."""

        current_count = (
            self.db.query(TeacherModel)
            .join(AcademicGroupModel, TeacherModel.id == AcademicGroupModel.teacher_id)
            .filter(
                TeacherModel.department_id == department_id,
                AcademicGroupModel.academic_period_id == academic_period_id,
            )
            .distinct(TeacherModel.id)
            .count()
        )

        previous_count = None
        if previous_period_id:
            previous_count = (
                self.db.query(TeacherModel)
                .join(
                    AcademicGroupModel, TeacherModel.id == AcademicGroupModel.teacher_id
                )
                .filter(
                    TeacherModel.department_id == department_id,
                    AcademicGroupModel.academic_period_id == previous_period_id,
                )
                .distinct(TeacherModel.id)
                .count()
            )

        return {
            "current_count": current_count,
            "previous_count": previous_count,
        }

    def get_history(self, teacher_id: int) -> dict | None:
        """Return the teacher's average score for each academic period."""

        teacher = self.get_by_id(teacher_id)

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
                AcademicPeriodModel.id.label("period_id"),
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
                AcademicPeriodModel.id,
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
                    "period_id": row.period_id,
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
    """Dependency injection for TeachersRepository."""

    return TeachersRepository(db)
