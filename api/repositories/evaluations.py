"""
Evaluations repository
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
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.evaluation import EvaluationFilters
from api.serializers.comments import comment_to_dict
from api.serializers.evaluations import evaluation_to_dict
from api.utils.dimensions import DIMENSION_MAP, QUESTIONS

QUESTION_TEXT: dict[str, str] = {q["code"]: q["text"] for q in QUESTIONS}


class EvaluationsRepository(BaseRepository[EvaluationModel]):
    """Evaluations repository"""

    def __init__(self, db: Session):
        super().__init__(EvaluationModel, db)

    def create_evaluation(
        self,
        user_id: int | None,
        academic_period_id: int,
        department_id: int,
        pdf_url: str,
        status: str = "PROCESSING",
    ) -> EvaluationModel:
        """Create a new evaluation record and return the model instance."""

        evaluation = EvaluationModel(
            user_id=user_id,
            academic_period_id=academic_period_id,
            department_id=department_id,
            pdf_url=pdf_url,
            status=status,
            count=None,
        )

        self.db.add(evaluation)
        self.db.flush()
        self.db.refresh(evaluation)

        return evaluation

    def get_by_id(self, evaluation_id: int) -> EvaluationModel | None:
        """Get an evaluation by ID."""

        return (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

    def get_by_id_as_dict(self, evaluation_id: int) -> dict | None:
        """Get an evaluation by ID as a dict."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        return evaluation_to_dict(evaluation)

    def search(
        self,
        filters: EvaluationFilters,
        pagination: PaginationParams,
    ) -> tuple[list[dict], int]:
        """Search evaluations with filters, pagination, and computed overall_average."""

        count_query = self.db.query(EvaluationModel.id).outerjoin(
            EvaluationModel.academic_period
        )
        count_query = self._apply_filters(count_query, filters)
        total = count_query.count()

        base_query = (
            self.db.query(
                EvaluationModel.id,
                EvaluationModel.user_id,
                EvaluationModel.academic_period_id,
                EvaluationModel.department_id,
                EvaluationModel.pdf_url,
                EvaluationModel.active,
                EvaluationModel.status,
                EvaluationModel.ai_status,
                EvaluationModel.count,
                EvaluationModel.created_at,
                EvaluationModel.updated_at,
                AcademicPeriodModel.name.label("period_name"),
                AcademicPeriodModel.code.label("period_code"),
                func.avg(EvaluationScoreModel.overall_average).label("overall_average"),
            )
            .outerjoin(EvaluationModel.academic_period)
            .outerjoin(
                EvaluationScoreModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .group_by(
                EvaluationModel.id,
                AcademicPeriodModel.id,
            )
        )

        base_query = self._apply_filters(base_query, filters)

        order_clause = EvaluationModel.created_at.desc()
        if filters.sort_by == "average_asc":
            order_clause = func.avg(EvaluationScoreModel.overall_average).asc()
        elif filters.sort_by == "average_desc":
            order_clause = func.avg(EvaluationScoreModel.overall_average).desc()

        evaluations = (
            base_query.order_by(order_clause)
            .offset(pagination.offset)
            .limit(pagination.limit)
            .all()
        )

        result = []
        for e in evaluations:
            result.append(
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "academic_period_id": e.academic_period_id,
                    "department_id": e.department_id,
                    "pdf_url": e.pdf_url,
                    "active": e.active,
                    "status": e.status,
                    "ai_status": e.ai_status,
                    "count": e.count,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                    "overall_average": (
                        float(e.overall_average) if e.overall_average else None
                    ),
                    "academic_period_name": e.period_name,
                    "academic_period_code": e.period_code,
                }
            )

        return result, total

    def _apply_filters(self, query, filters: EvaluationFilters):
        """Apply common filters to a query."""

        if filters.period_id is not None:
            query = query.filter(
                EvaluationModel.academic_period_id == filters.period_id
            )
        if filters.department_id is not None:
            query = query.filter(EvaluationModel.department_id == filters.department_id)
        if filters.status is not None:
            query = query.filter(EvaluationModel.status == filters.status)
        if filters.ai_status is not None:
            query = query.filter(EvaluationModel.ai_status == filters.ai_status)
        if filters.active is not None:
            query = query.filter(EvaluationModel.active == filters.active)
        if filters.search:
            pattern = f"%{filters.search}%"
            query = query.filter(AcademicPeriodModel.name.ilike(pattern))

        return query

    def get_by_period_id(self, academic_period_id: int) -> dict | None:
        """Get an evaluation by academic period ID."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.academic_period_id == academic_period_id)
            .first()
        )

        if not evaluation:
            return None

        return evaluation_to_dict(evaluation)

    def get_by_period_and_department(
        self, academic_period_id: int, department_id: int
    ) -> dict | None:
        """Get an evaluation by period and department combination."""

        evaluation = (
            self.db.query(EvaluationModel)
            .filter(
                EvaluationModel.academic_period_id == academic_period_id,
                EvaluationModel.department_id == department_id,
                EvaluationModel.active == True,
            )
            .first()
        )

        if not evaluation:
            return None

        return evaluation_to_dict(evaluation)

    def has_evaluations_for_period(self, academic_period_id: int) -> bool:
        """Check if any evaluations exist for a given academic period."""

        count = (
            self.db.query(EvaluationModel)
            .filter(EvaluationModel.academic_period_id == academic_period_id)
            .count()
        )

        return count > 0

    def update_active_status(self, evaluation_id: int, active: bool) -> dict | None:
        """Activate or deactivate an evaluation."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        evaluation.active = active
        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation_to_dict(evaluation)

    def update_status(
        self, evaluation_id: int, status: str, count: int | None = None
    ) -> dict | None:
        """Update the processing status and teacher count of an evaluation."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        evaluation.status = status

        if count is not None:
            evaluation.count = count

        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation_to_dict(evaluation)

    def delete_evaluation(self, evaluation_id: int) -> EvaluationModel | None:
        """Delete an evaluation and all its related records by ID."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        score_ids = [
            row[0]
            for row in self.db.query(EvaluationScoreModel.id)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .all()
        ]

        if score_ids:
            self.db.query(EvaluationQuestionScoreModel).filter(
                EvaluationQuestionScoreModel.evaluation_score_id.in_(score_ids)
            ).delete(synchronize_session="fetch")

        self.db.query(EvaluationScoreModel).filter(
            EvaluationScoreModel.evaluation_id == evaluation_id
        ).delete(synchronize_session="fetch")

        self.db.query(CommentModel).filter(
            CommentModel.evaluation_id == evaluation_id
        ).delete(synchronize_session="fetch")

        self.db.delete(evaluation)
        self.db.commit()

        return evaluation

    def get_teacher_comments(self, evaluation_id: int, teacher_id: int) -> dict | None:
        """Return comments grouped by course for a teacher within an evaluation."""

        evaluation = self.get_by_id(evaluation_id)
        if not evaluation:
            return None

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )
        if not teacher:
            return None

        rows = (
            self.db.query(CommentModel, AcademicGroupModel, CourseModel)
            .join(
                AcademicGroupModel,
                CommentModel.academic_groups_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(
                CommentModel.evaluation_id == evaluation_id,
                CommentModel.teacher_id == teacher_id,
            )
            .order_by(CourseModel.code, AcademicGroupModel.group_name)
            .all()
        )

        grouped: dict[tuple, dict] = {}
        for comment, academic_group, course in rows:
            if not comment.original_text:
                continue
            key = (course.code, academic_group.group_name)
            if key not in grouped:
                grouped[key] = {
                    "course_code": course.code,
                    "course_name": course.name,
                    "group_name": academic_group.group_name,
                    "comments": [],
                }
            grouped[key]["comments"].append(
                comment_to_dict(comment, group_name=academic_group.group_name)
            )

        return {
            "teacher_id": teacher_id,
            "evaluation_id": evaluation_id,
            "courses": list(grouped.values()),
        }

    def get_teacher_detail(self, evaluation_id: int, teacher_id: int) -> dict | None:
        """Return per-course and per-dimension scores for a teacher within an evaluation."""

        evaluation = self.get_by_id(evaluation_id)
        if not evaluation:
            return None

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )
        if not teacher:
            return None

        teacher_user = (
            self.db.query(UserModel).filter(UserModel.id == teacher.user_id).first()
            if teacher.user_id
            else None
        )

        score_rows = (
            self.db.query(EvaluationScoreModel, AcademicGroupModel, CourseModel)
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(CourseModel, AcademicGroupModel.course_id == CourseModel.id)
            .filter(
                EvaluationScoreModel.evaluation_id == evaluation_id,
                AcademicGroupModel.teacher_id == teacher_id,
            )
            .all()
        )

        if not score_rows:
            return None

        period = evaluation.academic_period
        courses = []
        accumulated: dict[str, list[float]] = {}

        for eval_score, group, course in score_rows:
            q_scores = (
                self.db.query(EvaluationQuestionScoreModel)
                .filter(
                    EvaluationQuestionScoreModel.evaluation_score_id == eval_score.id
                )
                .all()
            )

            group_q: dict[str, dict] = {
                qs.question_code: {"id": qs.id, "score": float(qs.score)}
                for qs in q_scores
            }

            for code, data in group_q.items():
                accumulated.setdefault(code, []).append(data["score"])

            group_dims = []
            for dim_name, codes in DIMENSION_MAP.items():
                dim_scores = [group_q[c]["score"] for c in codes if c in group_q]
                questions = [
                    {
                        "id": group_q[c]["id"],
                        "code": c,
                        "text": QUESTION_TEXT.get(c, c),
                        "score": group_q[c]["score"],
                    }
                    for c in codes
                    if c in group_q
                ]
                group_dims.append(
                    {
                        "dimension": dim_name,
                        "average": (
                            round(sum(dim_scores) / len(dim_scores), 2)
                            if dim_scores
                            else None
                        ),
                        "questions": questions,
                    }
                )

            courses.append(
                {
                    "course_code": course.code,
                    "course_name": course.name,
                    "group_name": group.group_name,
                    "respondent_count": eval_score.respondent_count or 0,
                    "overall_average": (
                        float(eval_score.overall_average)
                        if eval_score.overall_average
                        else None
                    ),
                    "dimensions": group_dims,
                }
            )

        overall_dims = []
        for dim_name, codes in DIMENSION_MAP.items():
            dim_scores = [s for c in codes for s in accumulated.get(c, [])]
            questions = []
            for code in codes:
                code_scores = accumulated.get(code, [])
                if code_scores:
                    questions.append(
                        {
                            "code": code,
                            "text": QUESTION_TEXT.get(code, code),
                            "score": round(sum(code_scores) / len(code_scores), 2),
                        }
                    )
            overall_dims.append(
                {
                    "dimension": dim_name,
                    "average": (
                        round(sum(dim_scores) / len(dim_scores), 2)
                        if dim_scores
                        else None
                    ),
                    "questions": questions,
                }
            )

        all_avgs = [
            c["overall_average"] for c in courses if c["overall_average"] is not None
        ]
        overall_avg = round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else None

        return {
            "teacher_id": teacher_id,
            "institutional_code": (
                teacher_user.institutional_code if teacher_user else None
            ),
            "name": teacher_user.name if teacher_user else None,
            "contract_type": teacher.contract_type,
            "evaluation_id": evaluation_id,
            "period_code": period.code if period else None,
            "period_name": period.name if period else None,
            "overall_average": overall_avg,
            "group_count": len(courses),
            "courses": courses,
            "dimensions": overall_dims,
        }

    def get_teachers_by_period(
        self,
        academic_period_id: int,
        pagination: PaginationParams,
        search: str | None = None,
    ) -> dict | None:
        """Return all teachers with their average evaluation scores for a given academic period."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == academic_period_id)
            .first()
        )
        if not period:
            return None

        base_query = (
            self.db.query(
                TeacherModel.id,
                UserModel.institutional_code,
                TeacherModel.contract_type,
                UserModel.name,
                UserModel.avatar_url,
                DepartmentModel.name.label("department_name"),
                func.count(EvaluationScoreModel.id).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("teacher_avg"),
            )
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(TeacherModel, AcademicGroupModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(DepartmentModel, TeacherModel.department_id == DepartmentModel.id)
            .join(
                EvaluationModel,
                EvaluationScoreModel.evaluation_id == EvaluationModel.id,
            )
            .filter(EvaluationModel.academic_period_id == academic_period_id)
        )

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.filter(
                (UserModel.name.ilike(search_pattern))
                | (UserModel.email.ilike(search_pattern))
            )

        base_query = base_query.group_by(
            TeacherModel.id,
            UserModel.institutional_code,
            TeacherModel.contract_type,
            UserModel.name,
            UserModel.avatar_url,
            DepartmentModel.name,
        )

        total = base_query.count()

        rows = (
            base_query.order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
            .all()
        )

        teachers = [
            {
                "teacher_id": row.id,
                "avatar_url": row.avatar_url if hasattr(row, "avatar_url") else None,
                "institutional_code": row.institutional_code,
                "name": row.name,
                "contract_type": row.contract_type,
                "department_name": row.department_name,
                "group_count": row.group_count,
                "overall_average": float(row.teacher_avg) if row.teacher_avg else None,
            }
            for row in rows
        ]

        return {
            "period_id": academic_period_id,
            "period_code": period.code,
            "period_name": period.name,
            "teacher_count": total,
            "teachers": teachers,
        }

    def get_summary(self, evaluation_id: int) -> dict | None:
        """Return aggregated statistics for an evaluation grouped by teacher."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        rows = (
            self.db.query(
                TeacherModel.id,
                UserModel.institutional_code,
                TeacherModel.contract_type,
                UserModel.name,
                func.count(EvaluationScoreModel.id).label("group_count"),
                func.avg(EvaluationScoreModel.overall_average).label("teacher_avg"),
            )
            .join(
                AcademicGroupModel,
                EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
            )
            .join(TeacherModel, AcademicGroupModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .group_by(
                TeacherModel.id,
                UserModel.institutional_code,
                TeacherModel.contract_type,
                UserModel.name,
            )
            .order_by(func.avg(EvaluationScoreModel.overall_average).desc())
            .all()
        )

        dept_avg = (
            self.db.query(func.avg(EvaluationScoreModel.overall_average))
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .scalar()
        )

        ranking = [
            {
                "rank": idx + 1,
                "teacher_id": row.id,
                "institutional_code": row.institutional_code,
                "name": row.name,
                "contract_type": row.contract_type,
                "group_count": row.group_count,
                "overall_average": float(row.teacher_avg) if row.teacher_avg else None,
            }
            for idx, row in enumerate(rows)
        ]

        period = evaluation.academic_period

        return {
            "evaluation_id": evaluation_id,
            "period_code": period.code if period else None,
            "period_name": period.name if period else None,
            "department_average": float(dept_avg) if dept_avg else None,
            "teacher_count": len(ranking),
            "best_teacher": ranking[0] if ranking else None,
            "worst_teacher": ranking[-1] if ranking else None,
            "ranking": ranking,
        }

    def get_dimension_averages(self, evaluation_id: int) -> list[dict] | None:
        """Return dimension-level averages aggregated across all groups for an evaluation."""

        evaluation = self.get_by_id(evaluation_id)

        if not evaluation:
            return None

        score_rows = (
            self.db.query(EvaluationScoreModel)
            .filter(EvaluationScoreModel.evaluation_id == evaluation_id)
            .all()
        )

        if not score_rows:
            return []

        accumulated: dict[str, list[float]] = {}

        for eval_score in score_rows:
            q_scores = (
                self.db.query(EvaluationQuestionScoreModel)
                .filter(
                    EvaluationQuestionScoreModel.evaluation_score_id == eval_score.id
                )
                .all()
            )

            for qs in q_scores:
                accumulated.setdefault(qs.question_code, []).append(float(qs.score))

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            dim_scores = [s for c in codes for s in accumulated.get(c, [])]
            questions = []
            for code in codes:
                code_scores = accumulated.get(code, [])
                if code_scores:
                    questions.append(
                        {
                            "code": code,
                            "text": QUESTION_TEXT.get(code, code),
                            "score": round(sum(code_scores) / len(code_scores), 2),
                        }
                    )
            dimensions.append(
                {
                    "dimension": dim_name,
                    "average": (
                        round(sum(dim_scores) / len(dim_scores), 2)
                        if dim_scores
                        else None
                    ),
                    "question_count": len(codes),
                    "questions": questions,
                }
            )

        return dimensions


def get_evaluations_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for EvaluationsRepository."""

    return EvaluationsRepository(db)
