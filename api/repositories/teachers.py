"""Repository for teacher-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.risk_level import RiskLevelModel
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
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .filter(UserModel.institutional_code == institutional_code)
            .first()
        )

    def get_by_institutional_codes(self, codes: list[str]) -> list[TeacherModel]:
        """Get existing teachers by a list of institutional codes."""

        if not codes:
            return []

        return (
            self.db.query(TeacherModel)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .filter(UserModel.institutional_code.in_(codes))
            .all()
        )

    def search(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
    ) -> tuple[list[TeacherModel], int]:
        """Search for teachers based on filters and pagination parameters."""

        query = (
            self.db.query(TeacherModel)
            .outerjoin(UserModel, TeacherModel.user_id == UserModel.id)
            .options(contains_eager(TeacherModel.user))
        )

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        UserModel.institutional_code.ilike(like_term),
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

        if filters.sort_by == "institutional_code_asc":
            query = query.order_by(UserModel.institutional_code.asc())
        elif filters.sort_by == "institutional_code_desc":
            query = query.order_by(UserModel.institutional_code.desc())
        elif filters.sort_by == "name_asc":
            query = query.order_by(UserModel.name.asc())
        elif filters.sort_by == "name_desc":
            query = query.order_by(UserModel.name.desc())
        else:
            query = query.order_by(TeacherModel.created_at.desc())

        return self.paginate(query, pagination)

    def search_with_averages(
        self,
        filters: TeacherFilters,
        pagination: PaginationParams,
        academic_period_id: int,
        has_average: bool = True,
        modality: str | None = None,
    ) -> tuple[list[tuple[TeacherModel, float | None, int]], int]:
        """Search teachers with their overall_average and count of ALTO-risk
        comments for a given academic period, selecting both in the same query
        so callers don't need extra aggregate lookups. Honors `filters.sort_by`,
        including sorting by average and by high-risk comment count.

        With a `modality`, both figures are computed over the groups of that
        kind of program only, so a teacher who does not teach in it drops out
        of the listing when `has_average` is on.

        Returns a list of (teacher, avg_score, high_risk_comments_count) tuples.
        """

        avg_subq = self._build_average_subquery(academic_period_id, modality)
        high_risk_subq = self._build_high_risk_comments_subquery(
            academic_period_id, modality
        )

        query = (
            self.db.query(
                TeacherModel,
                avg_subq.c.avg_score,
                func.coalesce(high_risk_subq.c.high_risk_count, 0).label(
                    "high_risk_comments_count"
                ),
            )
            .outerjoin(UserModel, TeacherModel.user_id == UserModel.id)
            .outerjoin(avg_subq, TeacherModel.id == avg_subq.c.teacher_id)
            .outerjoin(high_risk_subq, TeacherModel.id == high_risk_subq.c.teacher_id)
            .options(contains_eager(TeacherModel.user))
        )

        query = self._filter_by_has_average(query, avg_subq, has_average)

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        UserModel.institutional_code.ilike(like_term),
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

        if filters.sort_by == "overall_average_asc":
            query = query.order_by(
                func.coalesce(avg_subq.c.avg_score, 0).asc(),
                TeacherModel.id.asc(),
            )
        elif filters.sort_by == "overall_average_desc":
            query = query.order_by(
                func.coalesce(avg_subq.c.avg_score, 0).desc(),
                TeacherModel.id.asc(),
            )
        elif filters.sort_by == "high_risk_comments_count_asc":
            query = query.order_by(
                func.coalesce(high_risk_subq.c.high_risk_count, 0).asc(),
                TeacherModel.id.asc(),
            )
        elif filters.sort_by == "high_risk_comments_count_desc":
            query = query.order_by(
                func.coalesce(high_risk_subq.c.high_risk_count, 0).desc(),
                TeacherModel.id.asc(),
            )
        elif filters.sort_by == "institutional_code_asc":
            query = query.order_by(UserModel.institutional_code.asc())
        elif filters.sort_by == "institutional_code_desc":
            query = query.order_by(UserModel.institutional_code.desc())
        elif filters.sort_by == "name_asc":
            query = query.order_by(UserModel.name.asc())
        elif filters.sort_by == "name_desc":
            query = query.order_by(UserModel.name.desc())
        else:
            query = query.order_by(TeacherModel.created_at.desc())

        return self.paginate(query, pagination)

    def _build_average_subquery(
        self, academic_period_id: int, modality: str | None = None
    ):
        """Build a subquery of teacher average scores for an academic period,
        optionally over the groups of a single modality."""

        query = (
            self.db.query(
                AcademicGroupModel.teacher_id.label("teacher_id"),
                func.avg(EvaluationScoreModel.overall_average).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(
                EvaluationModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .filter(EvaluationModel.academic_period_id == academic_period_id)
        )

        if modality:
            query = query.filter(AcademicGroupModel.modality == modality)

        return query.group_by(AcademicGroupModel.teacher_id).subquery()

    def _build_high_risk_comments_subquery(
        self, academic_period_id: int, modality: str | None = None
    ):
        """Build a subquery counting ALTO-risk comments per teacher for an
        academic period, optionally over the groups of a single modality."""

        query = (
            self.db.query(
                CommentModel.teacher_id.label("teacher_id"),
                func.count(CommentModel.id).label("high_risk_count"),
            )
            .join(RiskLevelModel, CommentModel.risk_level == RiskLevelModel.id)
            .join(EvaluationModel, CommentModel.evaluation_id == EvaluationModel.id)
            .filter(
                EvaluationModel.academic_period_id == academic_period_id,
                RiskLevelModel.name == "ALTO",
            )
        )

        if modality:
            query = query.join(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            ).filter(AcademicGroupModel.modality == modality)

        return query.group_by(CommentModel.teacher_id).subquery()

    @staticmethod
    def _filter_by_has_average(query, avg_subq, has_average: bool):
        """Filter a query by whether teachers have an average score."""

        if has_average:
            return query.filter(avg_subq.c.avg_score.isnot(None))

        return query.filter(avg_subq.c.avg_score.is_(None))

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

    def get_history(
        self,
        teacher_id: int,
        pagination: PaginationParams,
        sort_by: str | None = None,
    ) -> tuple[list[dict], int, dict | None]:
        """Return the teacher's average score for each academic period, paginated."""

        teacher = self.get_by_id(teacher_id)

        if not teacher:
            return [], 0, None

        teacher_user = (
            self.db.query(UserModel).filter(UserModel.id == teacher.user_id).first()
            if teacher.user_id
            else None
        )

        base_query = (
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
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                AcademicPeriodModel.active == True,
                EvaluationModel.active == True,
            )
            .group_by(
                EvaluationModel.id,
                AcademicPeriodModel.code,
                AcademicPeriodModel.name,
                AcademicPeriodModel.id,
            )
        )

        order_clause = AcademicPeriodModel.code.asc()

        if sort_by == "period_code_desc":
            order_clause = AcademicPeriodModel.code.desc()
        elif sort_by == "overall_average_asc":
            order_clause = func.avg(EvaluationScoreModel.overall_average).asc()
        elif sort_by == "overall_average_desc":
            order_clause = func.avg(EvaluationScoreModel.overall_average).desc()
        elif sort_by == "group_count_asc":
            order_clause = func.count(EvaluationScoreModel.id).asc()
        elif sort_by == "group_count_desc":
            order_clause = func.count(EvaluationScoreModel.id).desc()

        base_query = base_query.order_by(order_clause)

        total = base_query.count()
        rows = base_query.offset(pagination.offset).limit(pagination.limit).all()

        teacher_info = {
            "teacher_id": teacher_id,
            "institutional_code": (
                teacher_user.institutional_code if teacher_user else None
            ),
            "name": teacher_user.name if teacher_user else None,
        }

        items = [
            {
                "evaluation_id": row.evaluation_id,
                "period_id": row.period_id,
                "period_code": row.period_code,
                "period_name": row.period_name,
                "overall_average": (float(row.avg_score) if row.avg_score else None),
                "group_count": row.group_count,
            }
            for row in rows
        ]

        return items, total, teacher_info


def get_teachers_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for TeachersRepository."""

    return TeachersRepository(db)
