"""
Improvement plans repository (Plan de Seguimiento Docente)
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.evaluation import EvaluationModel
from api.models.faculty import FacultyModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_case_report import ImprovementPlanCaseReportModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_checkpoint_note import (
    ImprovementPlanCheckpointNoteModel,
)
from api.models.improvement_plan_course import ImprovementPlanCourseModel
from api.models.improvement_plan_evidence import ImprovementPlanEvidenceModel
from api.models.improvement_plan_item import ImprovementPlanItemModel
from api.models.improvement_plan_item_comment import ImprovementPlanItemCommentModel
from api.models.improvement_plan_verification import ImprovementPlanVerificationModel
from api.models.improvement_plan_verification_item import (
    ImprovementPlanVerificationItemModel,
)
from api.models.program import ProgramModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.stats import StatsRepository
from api.schemas.improvement_plan import (
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanCourseCreate,
    ImprovementPlanCreate,
    ImprovementPlanItemCreate,
    ImprovementPlanUpdate,
)
from api.serializers.improvement_plans import improvement_plan_to_dict
from api.utils.dimensions import (
    ASPECT_NUMBERS,
    DIMENSION_MAP,
    QUESTION_TEXT,
    aspect_for_target,
)
from api.utils.improvement_suggestions import suggest_actions
from api.utils.plan_suggestion import HIGH_RISK_LEVEL_NAME, is_plan_suggested
from api.utils.program_codes import PROGRAM_CODE_LENGTH, program_code_of

# The two formal follow-ups of the official form: week 8 and weeks 15/16.
CHECKPOINT_STAGES = ["PRIMER_SEGUIMIENTO", "SEGUNDO_SEGUIMIENTO"]

MEASURABLE_TARGET_TYPES = ("OVERALL_AVERAGE", "DIMENSION", "QUESTION")

CLOSE_RESULT_TO_STATUS = {
    "CUMPLIDO": "CERRADO_CUMPLIDO",
    "NO_CUMPLIDO": "CERRADO_NO_CUMPLIDO",
}

# Every relationship ``improvement_plan_to_dict`` walks, loaded one batch per
# level instead of one query per plan. Lazy loading buys nothing here: the
# serializer always touches all of them, so the only thing deferring them adds
# is a round trip per plan and per relation — 91 queries to render a page of
# ten. ``selectinload`` and not ``joinedload`` because the listing is paginated
# and a joined collection would multiply the rows LIMIT counts.
# ``items.comment_links`` and ``checkpoints.aspect_notes`` are missing on
# purpose: both declare ``lazy="selectin"`` on the model, so they already come
# batched once their parent is loaded in one go.
PLAN_RELATIONS = (
    selectinload(ImprovementPlanModel.items),
    selectinload(ImprovementPlanModel.checkpoints),
    selectinload(ImprovementPlanModel.courses),
    selectinload(ImprovementPlanModel.documents),
    selectinload(ImprovementPlanModel.evidences),
    selectinload(ImprovementPlanModel.case_report),
    selectinload(ImprovementPlanModel.verifications)
    .selectinload(ImprovementPlanVerificationModel.items)
    .selectinload(ImprovementPlanVerificationItemModel.courses),
    selectinload(ImprovementPlanModel.verifications).selectinload(
        ImprovementPlanVerificationModel.comment_findings
    ),
)


class ImprovementPlansRepository:
    """Improvement plans repository"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _next_period_code(code: str) -> str | None:
        """Get the following academic period code from a code like '2025-1'."""

        parts = code.split("-")
        if len(parts) != 2:
            return None

        year = int(parts[0])
        semester = int(parts[1])

        if semester == 1:
            return f"{year}-2"
        return f"{year + 1}-1"

    def _period_code(self, period_id: int | None) -> str | None:
        # ``Session.get`` is the lookup by primary key, and unlike a filtered
        # query it *can* answer from the identity map. Do not count on that to
        # save a round trip, though: the identity map holds instances weakly, so
        # it only hits while something else keeps the row alive. Anything that
        # resolves several codes at once must use ``_period_codes`` instead.
        if not period_id:
            return None
        period = self.db.get(AcademicPeriodModel, period_id)
        return period.code if period else None

    def _period_by_code(self, code: str) -> AcademicPeriodModel | None:
        return (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.code == code)
            .first()
        )

    def _teacher_info(self, teacher_id: int) -> tuple[str | None, str | None]:
        """Return (name, avatar_url) for a teacher via its linked user."""

        row = (
            self.db.query(UserModel.name, UserModel.avatar_url)
            .join(TeacherModel, TeacherModel.user_id == UserModel.id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not row:
            return None, None
        return row[0], row[1]

    def _teacher_infos(
        self, teacher_ids: set[int]
    ) -> dict[int, tuple[str | None, str | None]]:
        """``_teacher_info`` for a whole batch of teachers, in one query."""

        if not teacher_ids:
            return {}

        rows = (
            self.db.query(TeacherModel.id, UserModel.name, UserModel.avatar_url)
            .join(UserModel, UserModel.id == TeacherModel.user_id)
            .filter(TeacherModel.id.in_(teacher_ids))
            .all()
        )

        return {row[0]: (row[1], row[2]) for row in rows}

    def _period_codes(self, period_ids: set[int]) -> dict[int, str]:
        """``_period_code`` for a whole batch of periods, in one query."""

        if not period_ids:
            return {}

        rows = (
            self.db.query(AcademicPeriodModel.id, AcademicPeriodModel.code)
            .filter(AcademicPeriodModel.id.in_(period_ids))
            .all()
        )

        return {row[0]: row[1] for row in rows}

    def _user_names(self, user_ids: set[int]) -> dict[int, str]:
        """Display names for a batch of users, in one query."""

        if not user_ids:
            return {}

        rows = (
            self.db.query(UserModel.id, UserModel.name)
            .filter(UserModel.id.in_(user_ids))
            .all()
        )

        return {row[0]: row[1] for row in rows}

    def _load(self, plan_id: int) -> ImprovementPlanModel | None:
        return (
            self.db.query(ImprovementPlanModel)
            .options(*PLAN_RELATIONS)
            .filter(ImprovementPlanModel.id == plan_id)
            .first()
        )

    def _enrich_many(self, plans: list[ImprovementPlanModel]) -> list[dict]:
        """Serialize a batch of plans resolving each lookup once for all of them.

        The three names the serializer needs — teacher, academic period and
        evidence uploader — are the same handful of rows across a whole page, so
        they are resolved per batch instead of per plan. Doing it per plan is
        what turned a listing into one query per name and per plan.
        """

        if not plans:
            return []

        teachers = self._teacher_infos({plan.teacher_id for plan in plans})
        periods = self._period_codes(
            {
                period_id
                for plan in plans
                for period_id in (plan.origin_period_id, plan.verification_period_id)
                if period_id
            }
        )
        uploader_names = self._user_names(
            {
                evidence.uploaded_by
                for plan in plans
                for evidence in plan.evidences
                if evidence.uploaded_by
            }
        )

        return [
            improvement_plan_to_dict(
                plan,
                teacher_name=teachers.get(plan.teacher_id, (None, None))[0],
                teacher_avatar_url=teachers.get(plan.teacher_id, (None, None))[1],
                origin_period_code=periods.get(plan.origin_period_id),
                verification_period_code=periods.get(plan.verification_period_id),
                evidence_uploader_names=uploader_names,
            )
            for plan in plans
        ]

    def _enrich(self, plan: ImprovementPlanModel) -> dict:
        return self._enrich_many([plan])[0]

    def get_teacher_user_id(self, teacher_id: int) -> int | None:
        """User id linked to a teacher (to check a DOCENTE owns the plan)."""

        row = (
            self.db.query(TeacherModel.user_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        return row[0] if row else None

    def get_teacher_by_user_id(self, user_id: int) -> TeacherModel | None:
        """Teacher record linked to a user, if any."""

        return (
            self.db.query(TeacherModel)
            .filter(TeacherModel.user_id == user_id)
            .first()
        )

    def get_department_director_user_id(self, department_id: int | None) -> int | None:
        """User id of the active director of a department, to notify them."""

        if department_id is None:
            return None

        row = (
            self.db.query(DirectorsModel.user_id)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active.is_(True),
            )
            .first()
        )

        return row[0] if row else None

    async def delete(self, plan_id: int) -> bool:
        """Remove a plan. Everything hanging off it goes with it.

        The seven child tables declare ``ondelete="CASCADE"``, so items,
        checkpoints, evidences, requests, courses, documents and the case report
        are the database's problem, not this method's.
        """

        plan = (
            self.db.query(ImprovementPlanModel)
            .filter(ImprovementPlanModel.id == plan_id)
            .first()
        )

        if not plan:
            return False

        self.db.delete(plan)
        self.db.commit()

        return True

    def get_teacher_contact(self, teacher_id: int) -> dict | None:
        """Who to tell when something happens to a teacher's plan.

        ``None`` when the teacher has no user account behind them: those exist
        (imported from an evaluation, never signed in) and there is nowhere to
        write to, which the caller has to be able to tell apart from a failure.
        """

        row = (
            self.db.query(
                UserModel.id.label("user_id"),
                UserModel.name,
                UserModel.email,
            )
            .select_from(TeacherModel)
            .join(UserModel, UserModel.id == TeacherModel.user_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )

        if not row:
            return None

        return {"user_id": row.user_id, "name": row.name, "email": row.email}

    def get_department_director_contact(self, department_id: int | None) -> dict | None:
        """Who to write to when something on a plan needs the director.

        The twin of ``get_teacher_contact`` for the other side of the loop:
        ``get_department_director_user_id`` above answers the bell, which only
        needs an id, but an email needs a name and an address as well.
        """

        if department_id is None:
            return None

        row = (
            self.db.query(
                UserModel.id.label("user_id"),
                UserModel.name,
                UserModel.email,
            )
            .select_from(DirectorsModel)
            .join(UserModel, UserModel.id == DirectorsModel.user_id)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active.is_(True),
            )
            .first()
        )

        if not row:
            return None

        return {"user_id": row.user_id, "name": row.name, "email": row.email}

    def get_teacher_department_id(self, teacher_id: int) -> int | None:
        """Department a teacher belongs to."""

        row = (
            self.db.query(TeacherModel.department_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )

        return row[0] if row else None

    def get_teacher_context(self, teacher_id: int) -> dict:
        """Header data the official forms print: código, departamento, facultad."""

        row = (
            self.db.query(
                UserModel.institutional_code,
                DepartmentModel.name.label("department_name"),
                FacultyModel.name.label("faculty_name"),
            )
            .select_from(TeacherModel)
            .outerjoin(UserModel, UserModel.id == TeacherModel.user_id)
            .outerjoin(
                DepartmentModel, DepartmentModel.id == TeacherModel.department_id
            )
            .outerjoin(FacultyModel, FacultyModel.id == DepartmentModel.faculty_id)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )

        if not row:
            return {"code": None, "department_name": None, "faculty_name": None}

        return {
            "code": row.institutional_code,
            "department_name": row.department_name,
            "faculty_name": row.faculty_name,
        }

    def get_department_context(self, department_id: int) -> dict:
        """Header data the official forms print for a whole department.

        Every candidate of a request belongs to the same department, so this is
        resolved once instead of per teacher as ``get_teacher_context`` does."""

        row = (
            self.db.query(
                DepartmentModel.name.label("department_name"),
                FacultyModel.name.label("faculty_name"),
            )
            .select_from(DepartmentModel)
            .outerjoin(FacultyModel, FacultyModel.id == DepartmentModel.faculty_id)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        if not row:
            return {"department_name": None, "faculty_name": None}

        return {
            "department_name": row.department_name,
            "faculty_name": row.faculty_name,
        }

    async def get_teacher_courses(self, teacher_id: int, period_id: int) -> list[dict]:
        """Asignaturas the teacher taught in a period, each with its carrera.

        Used to prefill the courses table of the official forms; the plan keeps
        its own snapshot of the rows the director actually chooses.

        The program comes from the code the asignatura already carries, not from
        the teacher's department: one teacher lectures the same subject across
        several careers, and the department only says where he is attached.
        Inactive programs still resolve — an old asignatura kept its carrera even
        after the registry closed it.
        """

        rows = (
            self.db.query(
                AcademicGroupModel.id,
                CourseModel.name.label("course_name"),
                CourseModel.code.label("course_code"),
                AcademicGroupModel.group_name,
                ProgramModel.name.label("program_name"),
            )
            .outerjoin(CourseModel, CourseModel.id == AcademicGroupModel.course_id)
            .outerjoin(
                ProgramModel,
                ProgramModel.code
                == func.substr(CourseModel.code, 1, PROGRAM_CODE_LENGTH),
            )
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                AcademicGroupModel.academic_period_id == period_id,
            )
            .order_by(CourseModel.name)
            .all()
        )

        return [
            {
                "academic_group_id": row.id,
                "course_name": row.course_name,
                "course_code": row.course_code,
                "group_name": row.group_name,
                "program_name": row.program_name,
            }
            for row in rows
        ]

    async def has_plan_for(self, teacher_id: int, origin_period_id: int) -> bool:
        """Whether a plan already exists for this teacher and origin period."""

        return (
            self.db.query(ImprovementPlanModel.id)
            .filter(
                ImprovementPlanModel.teacher_id == teacher_id,
                ImprovementPlanModel.origin_period_id == origin_period_id,
            )
            .first()
            is not None
        )

    def _teachers_with_plan(
        self, teacher_ids: list[int], origin_period_id: int
    ) -> set[int]:
        """Teachers from the list that already have a plan for the period."""

        if not teacher_ids:
            return set()

        rows = (
            self.db.query(ImprovementPlanModel.teacher_id)
            .filter(
                ImprovementPlanModel.teacher_id.in_(teacher_ids),
                ImprovementPlanModel.origin_period_id == origin_period_id,
            )
            .all()
        )

        return {row[0] for row in rows}

    def _high_risk_comment_counts(
        self, teacher_ids: list[int], period_id: int
    ) -> dict[int, int]:
        """High-risk comments each teacher got in the period.

        A teacher can keep every score above the threshold and still be the
        subject of a comment the AI classified as ALTO, which on its own is a
        reason to suggest a plan. Comments the analysis has not reached yet
        simply do not count."""

        if not teacher_ids:
            return {}

        rows = (
            self.db.query(
                CommentModel.teacher_id,
                func.count(CommentModel.id).label("total"),
            )
            .join(EvaluationModel, EvaluationModel.id == CommentModel.evaluation_id)
            .join(RiskLevelModel, RiskLevelModel.id == CommentModel.risk_level)
            .filter(
                CommentModel.teacher_id.in_(teacher_ids),
                EvaluationModel.academic_period_id == period_id,
                func.upper(RiskLevelModel.name) == HIGH_RISK_LEVEL_NAME,
            )
            .group_by(CommentModel.teacher_id)
            .all()
        )

        return {row.teacher_id: row.total for row in rows}

    # ------------------------------------------------------------------ #
    # Indicator averages (question = one item of the evaluation form)
    # ------------------------------------------------------------------ #
    def question_averages(
        self, teacher_ids: list[int], period_id: int
    ) -> dict[int, dict[str, float]]:
        """Per-teacher, per-question averages for a period, in a single query."""

        if not teacher_ids:
            return {}

        rows = (
            self.db.query(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .filter(
                AcademicGroupModel.teacher_id.in_(teacher_ids),
                EvaluationModel.academic_period_id == period_id,
            )
            .group_by(
                AcademicGroupModel.teacher_id,
                EvaluationQuestionScoreModel.question_code,
            )
            .all()
        )

        averages: dict[int, dict[str, float]] = {}
        for row in rows:
            averages.setdefault(row.teacher_id, {})[row.question_code] = round(
                float(row.avg_score), 2
            )

        return averages

    @staticmethod
    def dimension_average(
        question_averages: dict[str, float], codes: list[str]
    ) -> float | None:
        scores = [question_averages[c] for c in codes if c in question_averages]

        return round(sum(scores) / len(scores), 2) if scores else None

    def _build_indicators(
        self, question_averages: dict[str, float], threshold: float
    ) -> list[dict]:
        """Every dimension with its own average and the average of each of its
        questions, flagged against the institutional threshold."""

        dimensions = []

        for dimension, codes in DIMENSION_MAP.items():
            average = self.dimension_average(question_averages, codes)
            questions = []

            for code in codes:
                q_average = question_averages.get(code)
                questions.append(
                    {
                        "target_type": "QUESTION",
                        "target_ref": code,
                        "code": code,
                        "text": QUESTION_TEXT.get(code, code),
                        "average": q_average,
                        "below_threshold": (
                            q_average is not None and q_average <= threshold
                        ),
                        "suggestions": suggest_actions("QUESTION", code),
                    }
                )

            dimensions.append(
                {
                    "dimension": dimension,
                    "target_type": "DIMENSION",
                    "target_ref": dimension,
                    "average": average,
                    "below_threshold": average is not None and average <= threshold,
                    "suggestions": suggest_actions("DIMENSION", dimension),
                    "questions": questions,
                }
            )

        return dimensions

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    async def create(
        self, data: ImprovementPlanCreate, created_by: int | None = None
    ) -> dict:
        """Create a plan with its items and the three follow-up checkpoints."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == data.teacher_id)
            .first()
        )
        department_id = teacher.department_id if teacher else None

        verification_period_id = data.verification_period_id
        if verification_period_id is None:
            origin_code = self._period_code(data.origin_period_id)
            if origin_code:
                next_code = self._next_period_code(origin_code)
                if next_code:
                    next_period = self._period_by_code(next_code)
                    if next_period:
                        verification_period_id = next_period.id

        plan = ImprovementPlanModel(
            teacher_id=data.teacher_id,
            department_id=department_id,
            origin_period_id=data.origin_period_id,
            verification_period_id=verification_period_id,
            title=data.title,
            description=data.description,
            program_name=data.program_name,
            faculty_name=data.faculty_name,
            department_name=data.department_name,
            status="EN_SEGUIMIENTO",
            acta_status="BORRADOR",
            acta_number=data.acta_number,
            acta_date=data.acta_date,
            start_date=data.start_date,
            end_date=data.end_date,
            council_observations=data.council_observations,
            department_director_observations=data.department_director_observations,
            program_director_observations=data.program_director_observations,
            created_by=created_by,
        )

        for index, item in enumerate(data.items):
            plan.items.append(self._build_item(item, index))

        programs = self._programs_of(data.courses)

        for index, course in enumerate(data.courses):
            plan.courses.append(self._build_course(course, index, programs))

        # Both seguimientos are created upfront, each with its five aspect rows,
        # so the follow-up matrix of Formato 3 always renders complete.
        for stage in CHECKPOINT_STAGES:
            checkpoint = ImprovementPlanCheckpointModel(stage=stage, status="PENDIENTE")
            for aspect in ASPECT_NUMBERS:
                checkpoint.aspect_notes.append(
                    ImprovementPlanCheckpointNoteModel(aspect=aspect)
                )
            plan.checkpoints.append(checkpoint)

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    def _build_item(
        self, item: ImprovementPlanItemCreate, index: int
    ) -> ImprovementPlanItemModel:
        """Build an item, defaulting its form aspect from the targeted indicator."""

        target_type = item.target_type.value
        aspect = item.aspect or aspect_for_target(target_type, item.target_ref)

        model = ImprovementPlanItemModel(
            description=item.description,
            commitment=item.commitment,
            aspect=aspect,
            target_type=target_type,
            target_ref=item.target_ref,
            baseline_value=item.baseline_value,
            target_value=item.target_value,
            status=item.status.value if item.status else "PENDIENTE",
            order=item.order if item.order is not None else index,
        )

        for comment_id in item.comment_ids or []:
            model.comment_links.append(
                ImprovementPlanItemCommentModel(comment_id=comment_id)
            )

        return model

    def _programs_of(
        self, courses: list[ImprovementPlanCourseCreate]
    ) -> dict[str, str]:
        """COD_CARRERA -> program name, for every code the rows carry.

        One query for the whole table instead of one per row, and the answer is
        looked up by the prefix the course code embeds.
        """

        prefixes = {
            prefix
            for course in courses
            if (prefix := program_code_of(course.course_code)) is not None
        }

        if not prefixes:
            return {}

        rows = (
            self.db.query(ProgramModel.code, ProgramModel.name)
            .filter(ProgramModel.code.in_(prefixes))
            .all()
        )

        return {row.code: row.name for row in rows}

    def _build_course(
        self,
        course: ImprovementPlanCourseCreate,
        index: int,
        programs: dict[str, str],
    ) -> ImprovementPlanCourseModel:
        """Build one asignatura row of the official form header table.

        The carrera is read off the course code rather than taken from the
        payload: it is the registry's answer, and the client has no better one.
        What the payload sent only survives where the code cannot answer — a row
        typed by hand, or a code no program claims.
        """

        prefix = program_code_of(course.course_code)
        program_name = programs.get(prefix) if prefix else None

        return ImprovementPlanCourseModel(
            academic_group_id=course.academic_group_id,
            course_name=course.course_name,
            course_code=course.course_code,
            group_name=course.group_name,
            program_name=program_name or course.program_name,
            order=course.order if course.order is not None else index,
        )

    async def get_all(
        self,
        department_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        teacher_id: int | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get paginated plans with optional filters."""

        query = self.db.query(ImprovementPlanModel)

        if department_id is not None:
            query = query.filter(ImprovementPlanModel.department_id == department_id)
        if teacher_id is not None:
            query = query.filter(ImprovementPlanModel.teacher_id == teacher_id)
        if period_id is not None:
            query = query.filter(
                or_(
                    ImprovementPlanModel.origin_period_id == period_id,
                    ImprovementPlanModel.verification_period_id == period_id,
                )
            )
        if status:
            query = query.filter(ImprovementPlanModel.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = (
                query.join(TeacherModel, TeacherModel.id == ImprovementPlanModel.teacher_id)
                .join(UserModel, UserModel.id == TeacherModel.user_id)
                .filter(
                    or_(
                        ImprovementPlanModel.title.ilike(term),
                        UserModel.name.ilike(term),
                    )
                )
            )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        plans = (
            query.options(*PLAN_RELATIONS)
            .order_by(ImprovementPlanModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": self._enrich_many(plans),
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, plan_id: int) -> dict | None:
        """Get a single plan with items and checkpoints."""

        plan = self._load(plan_id)
        if not plan:
            return None
        return self._enrich(plan)

    async def update(self, plan_id: int, data: ImprovementPlanUpdate) -> dict | None:
        """Update plan fields and, if provided, replace its item list."""

        plan = self._load(plan_id)
        if not plan:
            return None

        payload = data.model_dump(exclude_unset=True)
        payload.pop("items", None)
        payload.pop("courses", None)

        for field, value in payload.items():
            setattr(plan, field, value)

        if data.items is not None:
            existing = {item.id: item for item in plan.items}
            incoming_ids: set[int] = set()

            for index, incoming in enumerate(data.items):
                if incoming.id and incoming.id in existing:
                    item = existing[incoming.id]
                    item.description = incoming.description
                    item.commitment = incoming.commitment
                    item.target_type = incoming.target_type.value
                    item.target_ref = incoming.target_ref
                    item.aspect = incoming.aspect or aspect_for_target(
                        item.target_type, item.target_ref
                    )
                    item.baseline_value = incoming.baseline_value
                    item.target_value = incoming.target_value
                    if incoming.status:
                        item.status = incoming.status.value
                    item.order = (
                        incoming.order if incoming.order is not None else index
                    )
                    if incoming.comment_ids is not None:
                        self._replace_item_comments(item, incoming.comment_ids)
                    incoming_ids.add(incoming.id)
                else:
                    plan.items.append(self._build_item(incoming, index))

            for item_id, item in existing.items():
                if item_id not in incoming_ids:
                    self.db.delete(item)

        if data.courses is not None:
            programs = self._programs_of(data.courses)

            for course in list(plan.courses):
                self.db.delete(course)
            plan.courses = [
                self._build_course(course, index, programs)
                for index, course in enumerate(data.courses)
            ]

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    def _replace_item_comments(
        self, item: ImprovementPlanItemModel, comment_ids: list[int]
    ) -> None:
        """Replace the student comments cited by an item."""

        wanted = set(comment_ids)
        current = {link.comment_id for link in item.comment_links}

        for link in list(item.comment_links):
            if link.comment_id not in wanted:
                item.comment_links.remove(link)

        for comment_id in wanted - current:
            item.comment_links.append(
                ImprovementPlanItemCommentModel(comment_id=comment_id)
            )

    # ------------------------------------------------------------------ #
    # Formato 1 — caso reportado por el programa académico
    # ------------------------------------------------------------------ #
    async def upsert_case_report(
        self,
        plan_id: int,
        data: ImprovementPlanCaseReportUpsert,
        reported_by: int | None = None,
    ) -> dict | None:
        """Create or update the Formato 1 case report attached to a plan."""

        plan = self._load(plan_id)
        if not plan:
            return None

        case_report = plan.case_report
        if case_report is None:
            case_report = ImprovementPlanCaseReportModel(reported_by=reported_by)
            plan.case_report = case_report

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(case_report, field, value)

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    # ------------------------------------------------------------------ #
    # Seguimientos (Formato 3)
    # ------------------------------------------------------------------ #
    def get_checkpoint(
        self, plan_id: int, checkpoint_id: int
    ) -> ImprovementPlanCheckpointModel | None:
        """A checkpoint of the given plan, or None if it belongs elsewhere."""

        return (
            self.db.query(ImprovementPlanCheckpointModel)
            .filter(
                ImprovementPlanCheckpointModel.id == checkpoint_id,
                ImprovementPlanCheckpointModel.plan_id == plan_id,
            )
            .first()
        )

    async def update_checkpoint(
        self,
        plan_id: int,
        checkpoint_id: int,
        data: ImprovementPlanCheckpointUpdate,
    ) -> dict | None:
        """Fill in one of the two formal seguimientos, per aspect."""

        checkpoint = self.get_checkpoint(plan_id, checkpoint_id)
        if not checkpoint:
            return None

        payload = data.model_dump(exclude_unset=True)
        payload.pop("aspect_notes", None)

        for field, value in payload.items():
            setattr(checkpoint, field, value)

        if checkpoint.status == "COMPLETADO" and checkpoint.completed_at is None:
            checkpoint.completed_at = datetime.now(timezone.utc)

        if data.aspect_notes is not None:
            by_aspect = {note.aspect: note for note in checkpoint.aspect_notes}
            for incoming in data.aspect_notes:
                note = by_aspect.get(incoming.aspect)
                if note is None:
                    note = ImprovementPlanCheckpointNoteModel(aspect=incoming.aspect)
                    checkpoint.aspect_notes.append(note)
                note.note = incoming.note

        self.db.commit()

        plan = self._load(plan_id)

        return self._enrich(plan) if plan else None

    async def get_by_teacher(self, teacher_id: int) -> list[dict]:
        """All plans of a teacher, newest first (for the teacher-facing view)."""

        plans = (
            self.db.query(ImprovementPlanModel)
            .options(*PLAN_RELATIONS)
            .filter(ImprovementPlanModel.teacher_id == teacher_id)
            .order_by(ImprovementPlanModel.created_at.desc())
            .all()
        )
        return self._enrich_many(plans)

    # ------------------------------------------------------------------ #
    # Acta de compromiso & evidences
    # ------------------------------------------------------------------ #
    async def set_acta_status(
        self,
        plan_id: int,
        status: str,
        closed_by: int | None = None,
    ) -> dict | None:
        """Move the acta through BORRADOR / CERRADA / FIRMADA."""

        plan = self._load(plan_id)
        if not plan:
            return None

        plan.acta_status = status

        # Both freezing states stamp the trace: an acta normally goes straight
        # from BORRADOR to FIRMADA when the signed scan lands, and skipping the
        # stamp there would lose who froze the agreement and when.
        if status in ("CERRADA", "FIRMADA"):
            plan.acta_closed_at = datetime.now(timezone.utc)
            plan.acta_closed_by = closed_by
        elif status == "BORRADOR":
            plan.acta_closed_at = None
            plan.acta_closed_by = None

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    async def add_evidence(
        self,
        plan_id: int,
        file_url: str,
        description: str | None = None,
        item_id: int | None = None,
        uploaded_by: int | None = None,
    ) -> dict | None:
        """Attach an evidence PDF to the plan (optionally tied to an item)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        if item_id is not None and not any(i.id == item_id for i in plan.items):
            raise ValueError("El ítem indicado no pertenece a este plan")

        plan.evidences.append(
            ImprovementPlanEvidenceModel(
                item_id=item_id,
                uploaded_by=uploaded_by,
                description=(description.strip() or None) if description else None,
                file_url=file_url,
            )
        )

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    def get_evidence(
        self, plan_id: int, evidence_id: int
    ) -> ImprovementPlanEvidenceModel | None:
        return (
            self.db.query(ImprovementPlanEvidenceModel)
            .filter(
                ImprovementPlanEvidenceModel.id == evidence_id,
                ImprovementPlanEvidenceModel.plan_id == plan_id,
            )
            .first()
        )

    async def delete_evidence(self, plan_id: int, evidence_id: int) -> dict | None:
        """Delete an evidence. Returns the enriched plan and the removed file
        url so the caller can delete it from disk."""

        evidence = self.get_evidence(plan_id, evidence_id)
        if not evidence:
            return None

        file_url = evidence.file_url
        self.db.delete(evidence)
        self.db.commit()

        plan = self._load(plan_id)

        return {
            "plan": self._enrich(plan) if plan else None,
            "file_url": file_url,
        }

    async def close(
        self, plan_id: int, result: str, reason: str | None = None
    ) -> dict | None:
        """Close a plan with the given result (CUMPLIDO / NO_CUMPLIDO)."""

        plan = self._load(plan_id)
        if not plan:
            return None

        # ``result`` is a ``CloseResult`` by the time it gets here, so the
        # mapping is total: a missing key would be a bug, not a plan to close
        # under some catch-all status.
        plan.status = CLOSE_RESULT_TO_STATUS[result]
        plan.close_reason = reason
        plan.closed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(plan)

        return self._enrich(plan)

    async def get_evaluated_periods(self, department_id: int) -> list[dict]:
        """Periods whose grades are already loaded for the department, newest
        first.

        A plan's origin period is the one where the low performance was
        detected, so only periods with an uploaded evaluation can be chosen —
        the current academic period usually has no grades yet (they arrive at
        the start of the next one)."""

        rows = (
            self.db.query(
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

    # ------------------------------------------------------------------ #
    # Candidates for a plan (auto-detección + sugerencias)
    # ------------------------------------------------------------------ #
    async def get_candidates(
        self,
        department_id: int,
        period_id: int,
        threshold: float,
        only_at_risk: bool = False,
        search: str | None = None,
    ) -> list[dict]:
        """Teachers of the department evaluated in the period, each with the
        average of every dimension and of every question of the form.

        A teacher can be below the threshold in a single question while keeping
        a healthy overall average, so by default the whole department is
        returned and the caller decides. ``only_at_risk`` narrows the list to
        the teachers a plan is suggested for (``is_plan_suggested``) that have
        no plan yet for the period — the auto-detection."""

        stats = StatsRepository(self.db)

        ranking = await stats.get_teacher_ranking_paginated(
            academic_period_id=period_id,
            department_id=department_id,
            page=1,
            limit=1000,
            search=search,
            sort="asc",
        )

        teachers = ranking.get("teachers", [])
        teacher_ids = [t["teacher_id"] for t in teachers]

        averages_by_teacher = self.question_averages(teacher_ids, period_id)
        planned = self._teachers_with_plan(teacher_ids, period_id)
        risky_comments = self._high_risk_comment_counts(teacher_ids, period_id)
        # The header of the official forms, so the creation page proposes it
        # already filled in instead of asking the director to type it.
        department_context = self.get_department_context(department_id)

        result: list[dict] = []

        for teacher in teachers:
            teacher_id = teacher["teacher_id"]
            avg = teacher.get("overall_average")
            below_threshold = avg is not None and avg <= threshold
            has_plan = teacher_id in planned

            dimensions = self._build_indicators(
                averages_by_teacher.get(teacher_id, {}), threshold
            )

            weak_questions = [
                {**question, "dimension": dimension["dimension"]}
                for dimension in dimensions
                for question in dimension["questions"]
                if question["below_threshold"]
            ]

            candidate = {
                "teacher_id": teacher_id,
                "name": teacher.get("name"),
                "avatar_url": teacher.get("avatar_url"),
                "institutional_code": teacher.get("institutional_code"),
                "overall_average": avg,
                "below_threshold": below_threshold,
                "has_plan": has_plan,
                "high_risk_comment_count": risky_comments.get(teacher_id, 0),
                "department_name": department_context["department_name"],
                "faculty_name": department_context["faculty_name"],
                "dimensions": dimensions,
                "weak_dimensions": [d for d in dimensions if d["below_threshold"]],
                "weak_questions": weak_questions,
                "overall_suggestions": suggest_actions("OVERALL_AVERAGE"),
            }

            if only_at_risk and (has_plan or not is_plan_suggested(candidate)):
                continue

            result.append(candidate)

        return result

    async def get_at_risk(
        self,
        department_id: int,
        period_id: int,
        threshold: float,
    ) -> list[dict]:
        """Teachers below threshold in the period without a plan yet."""

        return await self.get_candidates(
            department_id=department_id,
            period_id=period_id,
            threshold=threshold,
            only_at_risk=True,
        )

    # ------------------------------------------------------------------ #
    # Teacher history (evaluaciones por periodo + planes + reincidencia)
    # ------------------------------------------------------------------ #
    def _period_question_averages(
        self, teacher_id: int
    ) -> dict[str, dict[str, float]]:
        """Per-period, per-question averages for one teacher, in one query.

        Keyed by period code so it can be merged with the overall history."""

        rows = (
            self.db.query(
                AcademicPeriodModel.code.label("period_code"),
                EvaluationQuestionScoreModel.question_code,
                func.avg(EvaluationQuestionScoreModel.score).label("avg_score"),
            )
            .join(
                EvaluationScoreModel,
                EvaluationScoreModel.id
                == EvaluationQuestionScoreModel.evaluation_score_id,
            )
            .join(
                AcademicGroupModel,
                AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
            )
            .join(
                EvaluationModel,
                EvaluationModel.id == EvaluationScoreModel.evaluation_id,
            )
            .join(
                AcademicPeriodModel,
                AcademicPeriodModel.id == EvaluationModel.academic_period_id,
            )
            .filter(AcademicGroupModel.teacher_id == teacher_id)
            .group_by(
                AcademicPeriodModel.code,
                EvaluationQuestionScoreModel.question_code,
            )
            .all()
        )

        averages: dict[str, dict[str, float]] = {}
        for row in rows:
            averages.setdefault(row.period_code, {})[row.question_code] = round(
                float(row.avg_score), 2
            )

        return averages

    @staticmethod
    def _indicator_label(target_type: str, target_ref: str | None) -> str:
        if target_type == "OVERALL_AVERAGE":
            return "Promedio general"
        if target_type == "QUESTION" and target_ref:
            return f"{target_ref} — {QUESTION_TEXT.get(target_ref, target_ref)}"
        return target_ref or target_type

    async def get_history(self, teacher_id: int) -> dict | None:
        """Full follow-up history of a teacher: overall + per-dimension average
        for every evaluated period, every improvement plan with its resolution,
        and the indicators the teacher relapsed on (same indicator targeted by
        plans of different origin periods)."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.id == teacher_id)
            .first()
        )
        if not teacher:
            return None

        stats = StatsRepository(self.db)
        overall_history = await stats.get_teacher_history(teacher_id) or []
        question_history = self._period_question_averages(teacher_id)

        periods = [
            {
                "period_code": entry["period_code"],
                "period_name": entry["period_name"],
                "overall_average": entry["overall_average"],
                "dimensions": {
                    dimension: self.dimension_average(
                        question_history.get(entry["period_code"], {}), codes
                    )
                    for dimension, codes in DIMENSION_MAP.items()
                },
            }
            for entry in overall_history
        ]

        plans = (
            self.db.query(ImprovementPlanModel)
            .options(*PLAN_RELATIONS)
            .filter(ImprovementPlanModel.teacher_id == teacher_id)
            .order_by(ImprovementPlanModel.created_at.asc())
            .all()
        )

        origin_codes = self._period_codes(
            {plan.origin_period_id for plan in plans if plan.origin_period_id}
        )

        groups: dict[tuple[str, str | None], dict] = {}
        for plan in plans:
            origin_code = origin_codes.get(plan.origin_period_id)
            for item in plan.items:
                if item.target_type == "QUALITATIVE":
                    continue
                group = groups.setdefault(
                    (item.target_type, item.target_ref),
                    {"plan_ids": [], "origin_period_ids": set(), "period_codes": []},
                )
                if plan.id not in group["plan_ids"]:
                    group["plan_ids"].append(plan.id)
                    group["origin_period_ids"].add(plan.origin_period_id)
                    if origin_code:
                        group["period_codes"].append(origin_code)

        recurrences = [
            {
                "target_type": target_type,
                "target_ref": target_ref,
                "label": self._indicator_label(target_type, target_ref),
                "plan_ids": group["plan_ids"],
                "period_codes": group["period_codes"],
            }
            for (target_type, target_ref), group in groups.items()
            if len(group["origin_period_ids"]) >= 2
        ]

        name, avatar = self._teacher_info(teacher_id)

        return {
            "teacher_id": teacher_id,
            "teacher_name": name,
            "teacher_avatar_url": avatar,
            "department_id": teacher.department_id,
            "periods": periods,
            "plans": self._enrich_many(plans),
            "recurrences": recurrences,
        }


def get_improvement_plans_repository(db: Annotated[Session, Depends(get_db)]):
    """Get improvement plans repository"""

    return ImprovementPlansRepository(db)
