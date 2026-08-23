"""
Verification of improvement plans against the semester that follows them.

An improvement plan is closed when the Formato 3 is signed, at the end of the
accompaniment. The grades that would prove the teacher actually improved belong
to the *next* semester and do not exist yet at that point, so the closing can
never be the moment of the comparison. This module is that comparison, run on
its own when the evaluation of the verification period is uploaded.

It writes to ``improvement_plan_verifications`` and never touches the closing
the director signed: what was agreed, presented and signed stays as it is, and
this is the answer that arrives afterwards.

Two passes, because the two inputs are ready at different moments:

- ``verify_scores_for_evaluation`` runs when the evaluation finishes
  processing, since the numbers are persisted right there
- ``verify_comments_for_evaluation`` runs when the AI analysis finishes, since
  comments carry no risk level nor pedagogical category until then

Both are idempotent per (plan, period) and best-effort: a verification that
fails must never undo an upload that succeeded.
"""

import asyncio
import datetime
import logging

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from api.core.websockets.connection_manager import (
    connection_manager as notification_manager,
)
from api.core.websockets.events import NotificationEvent
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.comment_pedagogical_category import CommentPedagogicalCategoryModel
from api.models.course import CourseModel
from api.models.director import DirectorsModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_item_comment import ImprovementPlanItemCommentModel
from api.models.improvement_plan_verification import ImprovementPlanVerificationModel
from api.models.improvement_plan_verification_comment import (
    ImprovementPlanVerificationCommentModel,
)
from api.models.improvement_plan_verification_course import (
    ImprovementPlanVerificationCourseModel,
)
from api.models.improvement_plan_verification_item import (
    ImprovementPlanVerificationItemModel,
)
from api.models.notification import NotificationModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.repositories.improvement_plans import (
    MEASURABLE_TARGET_TYPES,
    ImprovementPlansRepository,
)
from api.repositories.settings import SettingsRepository
from api.services.improvement_plan_service import (
    DEFAULT_SCORE_THRESHOLD,
    SCORE_THRESHOLD_SETTING,
)
from api.utils.dimensions import DIMENSION_MAP, QUESTION_TEXT
from api.utils.plan_links import manager_plan_path
from api.utils.plan_suggestion import HIGH_RISK_LEVEL_NAME

logger = logging.getLogger(__name__)

# Only ALTO raises the alert: it is the level the whole system already treats as
# worth acting on (see api/utils/plan_suggestion.py), so alerting on MEDIO here
# would flag teachers no plan would ever have been suggested for. MEDIO is kept
# as context instead of dropped, so the director still sees the trend.
CONTEXT_RISK_LEVEL_NAME = "MEDIO"
TRACKED_RISK_LEVEL_NAMES = (HIGH_RISK_LEVEL_NAME, CONTEXT_RISK_LEVEL_NAME)

# A plan still being drafted has nothing agreed to verify.
DRAFT_PLAN_STATUS = "BORRADOR"

SCORES_ALERT_TITLE = "Un docente no alcanzó la meta de su plan"
COURSE_ALERT_TITLE = "Meta alcanzada en general, pero baja en una asignatura"
COMMENTS_ALERT_TITLE = "Reincidencia en las observaciones de estudiantes"

# How many findings the message spells out before summarising with "y N más".
MAX_LISTED_FINDINGS = 3


# --------------------------------------------------------------------------- #
# Which plans this period settles                                             #
# --------------------------------------------------------------------------- #
def _previous_period_code(code: str) -> str | None:
    """The code of the period an improvement plan would have been born in for
    ``code`` to be its verification period. Inverse of
    ``ImprovementPlansRepository._next_period_code``."""

    parts = code.split("-")

    if len(parts) != 2:
        return None

    try:
        year = int(parts[0])
        semester = int(parts[1])
    except ValueError:
        return None

    if semester == 2:
        return f"{year}-1"

    return f"{year - 1}-2"


def plans_to_verify(
    db, period_id: int, teacher_ids: list[int] | None = None
) -> list[ImprovementPlanModel]:
    """Plans whose verification period is ``period_id``.

    ``verification_period_id`` is resolved when the plan is created, but it is
    left null when the following period did not exist in the catalogue yet —
    which is the normal case, since the plan is drawn up before that semester
    starts. Those plans are matched by walking back from the period code, and
    the pointer is filled in on the way so it stops being a special case.
    """

    period = (
        db.query(AcademicPeriodModel)
        .filter(AcademicPeriodModel.id == period_id)
        .first()
    )

    if not period:
        return []

    query = db.query(ImprovementPlanModel).options(
        joinedload(ImprovementPlanModel.items)
    )

    origin_code = _previous_period_code(period.code) if period.code else None
    origin = (
        db.query(AcademicPeriodModel)
        .filter(AcademicPeriodModel.code == origin_code)
        .first()
        if origin_code
        else None
    )

    if origin:
        matches = (ImprovementPlanModel.verification_period_id == period_id) | (
            (ImprovementPlanModel.verification_period_id.is_(None))
            & (ImprovementPlanModel.origin_period_id == origin.id)
        )
    else:
        matches = ImprovementPlanModel.verification_period_id == period_id

    query = query.filter(
        matches, ImprovementPlanModel.status != DRAFT_PLAN_STATUS
    )

    if teacher_ids is not None:
        if not teacher_ids:
            return []
        query = query.filter(ImprovementPlanModel.teacher_id.in_(teacher_ids))

    plans = query.all()

    for plan in plans:
        if plan.verification_period_id is None:
            plan.verification_period_id = period_id

    return plans


def evaluated_teacher_ids(db, evaluation_id: int) -> list[int]:
    """Teachers this evaluation brought grades for."""

    rows = (
        db.query(AcademicGroupModel.teacher_id)
        .join(
            EvaluationScoreModel,
            EvaluationScoreModel.academic_group_id == AcademicGroupModel.id,
        )
        .filter(
            EvaluationScoreModel.evaluation_id == evaluation_id,
            AcademicGroupModel.teacher_id.isnot(None),
        )
        .distinct()
        .all()
    )

    return [row[0] for row in rows]


# --------------------------------------------------------------------------- #
# Reading the verification period                                             #
# --------------------------------------------------------------------------- #
def _group_question_averages(
    db, teacher_id: int, period_id: int
) -> tuple[dict[int, dict[str, float]], dict[int, dict]]:
    """Per-question averages broken down by academic group, plus the name of
    each group.

    These are the groups of the verification period, not the ones printed on
    the plan: an academic group belongs to a single period, so what
    ``improvement_plan_courses`` froze cannot be measured again. It also covers
    the case that matters most — the same shortcoming reappearing in a
    different subject.
    """

    rows = (
        db.query(
            AcademicGroupModel.id.label("group_id"),
            CourseModel.name.label("course_name"),
            CourseModel.code.label("course_code"),
            AcademicGroupModel.group_name,
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
        .outerjoin(CourseModel, CourseModel.id == AcademicGroupModel.course_id)
        .filter(
            AcademicGroupModel.teacher_id == teacher_id,
            EvaluationModel.academic_period_id == period_id,
        )
        .group_by(
            AcademicGroupModel.id,
            CourseModel.name,
            CourseModel.code,
            AcademicGroupModel.group_name,
            EvaluationQuestionScoreModel.question_code,
        )
        .all()
    )

    averages: dict[int, dict[str, float]] = {}
    groups: dict[int, dict] = {}

    for row in rows:
        averages.setdefault(row.group_id, {})[row.question_code] = round(
            float(row.avg_score), 2
        )
        groups[row.group_id] = {
            "course_name": row.course_name,
            "course_code": row.course_code,
            "group_name": row.group_name,
        }

    return averages, groups


def _group_overall_averages(db, teacher_id: int, period_id: int) -> dict[int, float]:
    """The overall average of each group the teacher taught in the period."""

    rows = (
        db.query(
            AcademicGroupModel.id.label("group_id"),
            func.avg(EvaluationScoreModel.overall_average).label("avg_score"),
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
            AcademicGroupModel.teacher_id == teacher_id,
            EvaluationModel.academic_period_id == period_id,
            EvaluationScoreModel.overall_average.isnot(None),
        )
        .group_by(AcademicGroupModel.id)
        .all()
    )

    return {row.group_id: round(float(row.avg_score), 2) for row in rows}


def _overall_average(db, teacher_id: int, period_id: int) -> float | None:
    """The teacher's overall average for the period, over all their groups —
    the same figure the stats module reports."""

    value = (
        db.query(func.avg(EvaluationScoreModel.overall_average))
        .join(
            AcademicGroupModel,
            AcademicGroupModel.id == EvaluationScoreModel.academic_group_id,
        )
        .join(
            EvaluationModel,
            EvaluationModel.id == EvaluationScoreModel.evaluation_id,
        )
        .filter(
            AcademicGroupModel.teacher_id == teacher_id,
            EvaluationModel.academic_period_id == period_id,
        )
        .scalar()
    )

    return round(float(value), 2) if value is not None else None


# --------------------------------------------------------------------------- #
# Pass 1 — the agreed targets against the new grades                          #
# --------------------------------------------------------------------------- #
def _indicator_value(
    target_type: str,
    target_ref: str | None,
    overall: float | None,
    question_averages: dict[str, float],
) -> float | None:
    """What the indicator of an item is worth in a set of averages."""

    if target_type == "OVERALL_AVERAGE":
        return overall

    if target_type == "DIMENSION" and target_ref:
        codes = DIMENSION_MAP.get(target_ref, [])
        scores = [question_averages[c] for c in codes if c in question_averages]

        return round(sum(scores) / len(scores), 2) if scores else None

    if target_type == "QUESTION" and target_ref:
        return question_averages.get(target_ref)

    return None


def _indicator_label(target_type: str, target_ref: str | None) -> str:
    """How the indicator reads in a notification."""

    if target_type == "OVERALL_AVERAGE":
        return "el promedio general"

    if target_type == "DIMENSION" and target_ref:
        return f"la dimensión «{target_ref}»"

    if target_type == "QUESTION" and target_ref:
        return f"«{QUESTION_TEXT.get(target_ref, target_ref)}»"

    return "el indicador comprometido"


def _upsert_verification(
    db, plan_id: int, period_id: int, evaluation_id: int | None
) -> ImprovementPlanVerificationModel:
    """The verification row of a (plan, period), created on first sight.

    One row per pair, so re-processing or re-analysing the same evaluation
    rewrites the findings instead of piling up a second set.
    """

    verification = (
        db.query(ImprovementPlanVerificationModel)
        .filter(
            ImprovementPlanVerificationModel.plan_id == plan_id,
            ImprovementPlanVerificationModel.period_id == period_id,
        )
        .first()
    )

    if verification is None:
        verification = ImprovementPlanVerificationModel(
            plan_id=plan_id, period_id=period_id
        )
        db.add(verification)
        db.flush()

    if evaluation_id:
        verification.evaluation_id = evaluation_id

    return verification


def verify_plan_scores(
    db,
    plan: ImprovementPlanModel,
    period_id: int,
    threshold: float,
    evaluation_id: int | None = None,
) -> ImprovementPlanVerificationModel | None:
    """Measure every agreed target of ``plan`` against ``period_id``.

    The verdict is the teacher's average over **all** their groups of the
    period: that is the figure the acta agreed on. The same indicator is also
    broken down per subject, because a teacher can clear the target overall and
    still be under it in one course — worth telling the director, but not what
    was signed.

    The plan's own items are deliberately left untouched: they were printed and
    signed on the Formato 3, and this comparison arrives afterwards.
    """

    items = [
        item for item in plan.items if item.target_type in MEASURABLE_TARGET_TYPES
    ]

    if not items:
        return None

    repository = ImprovementPlansRepository(db)
    question_averages = repository.question_averages([plan.teacher_id], period_id).get(
        plan.teacher_id, {}
    )
    overall = _overall_average(db, plan.teacher_id, period_id)
    group_question_averages, groups = _group_question_averages(
        db, plan.teacher_id, period_id
    )
    group_overall = _group_overall_averages(db, plan.teacher_id, period_id)

    verification = _upsert_verification(db, plan.id, period_id, evaluation_id)

    for previous in list(verification.items):
        db.delete(previous)
    db.flush()

    measured = 0
    met_count = 0

    for item in items:
        target = (
            float(item.target_value)
            if item.target_value is not None
            else float(threshold)
        )
        value = _indicator_value(
            item.target_type, item.target_ref, overall, question_averages
        )
        met = None if value is None else value >= target

        row = ImprovementPlanVerificationItemModel(
            verification_id=verification.id,
            item_id=item.id,
            target_type=item.target_type,
            target_ref=item.target_ref,
            target_value=target,
            result_value=value,
            met=met,
        )
        db.add(row)
        db.flush()

        if value is not None:
            measured += 1
            if met:
                met_count += 1

        for group_id, group in groups.items():
            group_value = _indicator_value(
                item.target_type,
                item.target_ref,
                group_overall.get(group_id),
                group_question_averages.get(group_id, {}),
            )

            if group_value is None:
                continue

            db.add(
                ImprovementPlanVerificationCourseModel(
                    verification_item_id=row.id,
                    academic_group_id=group_id,
                    course_name=group["course_name"],
                    course_code=group["course_code"],
                    group_name=group["group_name"],
                    result_value=group_value,
                    met=group_value >= target,
                )
            )

    if measured == 0:
        verification.result = "SIN_DATOS"
    elif met_count == measured:
        verification.result = "MEJORO"
    else:
        verification.result = "NO_MEJORO"

    verification.scores_verified_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()

    return verification


# --------------------------------------------------------------------------- #
# Pass 2 — the student comments that come back                                #
# --------------------------------------------------------------------------- #
def _cited_categories(db, item_ids: list[int]) -> dict[int, set[int]]:
    """Pedagogical categories of the comments each qualitative item cites.

    This is what makes the comparison a comparison. A plan item born of a
    comment about punctuality is answered by punctuality complaints coming
    back, not by any high-risk comment of the semester — the teacher could be
    flagged for something the plan never spoke about.
    """

    if not item_ids:
        return {}

    rows = (
        db.query(
            ImprovementPlanItemCommentModel.item_id,
            CommentPedagogicalCategoryModel.pedagogical_category_id,
        )
        .join(
            CommentPedagogicalCategoryModel,
            CommentPedagogicalCategoryModel.comment_id
            == ImprovementPlanItemCommentModel.comment_id,
        )
        .filter(ImprovementPlanItemCommentModel.item_id.in_(item_ids))
        .distinct()
        .all()
    )

    categories: dict[int, set[int]] = {}

    for item_id, category_id in rows:
        categories.setdefault(item_id, set()).add(category_id)

    return categories


def _period_comments(db, teacher_id: int, period_id: int) -> list:
    """The teacher's comments in a period, with their risk level and every
    category the AI gave them. Only the two levels worth tracking."""

    return (
        db.query(
            CommentModel.id.label("comment_id"),
            RiskLevelModel.name.label("risk_level_name"),
            CommentPedagogicalCategoryModel.pedagogical_category_id.label(
                "category_id"
            ),
            PedagogicalCategoryModel.name.label("category_name"),
        )
        .join(EvaluationModel, EvaluationModel.id == CommentModel.evaluation_id)
        .join(RiskLevelModel, RiskLevelModel.id == CommentModel.risk_level)
        .outerjoin(
            CommentPedagogicalCategoryModel,
            CommentPedagogicalCategoryModel.comment_id == CommentModel.id,
        )
        .outerjoin(
            PedagogicalCategoryModel,
            PedagogicalCategoryModel.id
            == CommentPedagogicalCategoryModel.pedagogical_category_id,
        )
        .filter(
            CommentModel.teacher_id == teacher_id,
            EvaluationModel.academic_period_id == period_id,
            RiskLevelModel.name.in_(TRACKED_RISK_LEVEL_NAMES),
        )
        .all()
    )


def verify_plan_comments(
    db,
    plan: ImprovementPlanModel,
    period_id: int,
    evaluation_id: int | None = None,
) -> ImprovementPlanVerificationModel | None:
    """Look for the complaint of a qualitative commitment coming back.

    Only ALTO raises the alert; MEDIO is recorded as context. And this is never
    a verdict against a target — there is no number to compare — so it is
    reported as reincidencia, with the comments listed for the director to read.
    """

    qualitative = [
        item for item in plan.items if item.target_type not in MEASURABLE_TARGET_TYPES
    ]

    if not qualitative:
        return None

    categories_by_item = _cited_categories(db, [item.id for item in qualitative])
    comments = _period_comments(db, plan.teacher_id, period_id)

    verification = _upsert_verification(db, plan.id, period_id, evaluation_id)

    for previous in list(verification.comment_findings):
        db.delete(previous)
    db.flush()

    seen: set[tuple[int | None, int]] = set()

    for item_id, category_ids in categories_by_item.items():
        for row in comments:
            if row.category_id not in category_ids:
                continue
            if (item_id, row.comment_id) in seen:
                continue

            seen.add((item_id, row.comment_id))
            db.add(
                ImprovementPlanVerificationCommentModel(
                    verification_id=verification.id,
                    item_id=item_id,
                    comment_id=row.comment_id,
                    pedagogical_category_id=row.category_id,
                    category_name=row.category_name,
                    risk_level_name=row.risk_level_name,
                    is_alert=row.risk_level_name == HIGH_RISK_LEVEL_NAME,
                )
            )

    # The plan cited comments the AI never categorised — usually older ones, or
    # a comment the model could not place. Falling back to the plain rule keeps
    # the commitment verified instead of silently skipped.
    if not categories_by_item:
        for row in comments:
            if row.risk_level_name != HIGH_RISK_LEVEL_NAME:
                continue
            if (None, row.comment_id) in seen:
                continue

            seen.add((None, row.comment_id))
            db.add(
                ImprovementPlanVerificationCommentModel(
                    verification_id=verification.id,
                    item_id=None,
                    comment_id=row.comment_id,
                    pedagogical_category_id=row.category_id,
                    category_name=row.category_name,
                    risk_level_name=row.risk_level_name,
                    is_alert=True,
                )
            )

    verification.comments_verified_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()

    return verification


# --------------------------------------------------------------------------- #
# Telling the director                                                        #
# --------------------------------------------------------------------------- #
def _director_user_id(db, plan, fallback_department_id: int | None) -> int | None:
    """Who followed the plan up. Plans carry their own department, but it is
    nullable, so the evaluation's own department is the fallback."""

    department_id = plan.department_id or fallback_department_id

    if not department_id:
        return None

    director = (
        db.query(DirectorsModel)
        .filter(DirectorsModel.department_id == department_id)
        .first()
    )

    return director.user_id if director else None


def _teacher_name(db, teacher_id: int) -> str:
    contact = ImprovementPlansRepository(db).get_teacher_contact(teacher_id)

    return (contact or {}).get("name") or "Un docente"


def _send(db, user_id: int, title: str, message: str, link: str) -> None:
    """Bell notification plus its WebSocket push, in the shape the rest of the
    processor uses."""

    notification = NotificationModel(
        user_id=user_id,
        title=title,
        message=message,
        type="warning",
        link=link,
    )
    db.add(notification)
    db.flush()

    event = NotificationEvent(
        notification_id=notification.id,
        user_id=user_id,
        title=title,
        message=message,
        notification_type="warning",
        link=link,
    )

    channel = f"notifications:{user_id}"

    try:
        asyncio.get_running_loop()
        asyncio.ensure_future(notification_manager.broadcast(channel, event))
    except RuntimeError:
        asyncio.run(notification_manager.broadcast(channel, event))


def _listed(entries: list[str]) -> str:
    """The first few findings spelled out, the rest counted."""

    shown = "; ".join(entries[:MAX_LISTED_FINDINGS])
    rest = len(entries) - MAX_LISTED_FINDINGS

    return f"{shown} y {rest} más" if rest > 0 else shown


def _notify_scores(
    db, plan, verification, period_code: str | None, department_id: int | None
) -> None:
    """Tell the director when a target was missed, or when it was reached
    overall but not in every subject."""

    if verification.scores_notified_at:
        return

    rows = (
        db.query(ImprovementPlanVerificationItemModel)
        .filter(
            ImprovementPlanVerificationItemModel.verification_id == verification.id
        )
        .all()
    )

    measured = [row for row in rows if row.met is not None]

    if not measured:
        return

    user_id = _director_user_id(db, plan, department_id)

    if not user_id:
        return

    teacher = _teacher_name(db, plan.teacher_id)
    where = f" en {period_code}" if period_code else ""
    link = manager_plan_path(plan.id)

    failed = [row for row in measured if row.met is False]

    if failed:
        findings = [
            f"{_indicator_label(row.target_type, row.target_ref)} quedó en "
            f"{float(row.result_value):.2f} frente a la meta "
            f"{float(row.target_value):.2f}"
            for row in failed
        ]
        message = (
            f"{teacher} no alcanzó {len(failed)} de {len(measured)} "
            f"{'meta' if len(measured) == 1 else 'metas'} del plan "
            f"«{plan.title}»{where}: {_listed(findings)}."
        )
        _send(db, user_id, SCORES_ALERT_TITLE, message, link)
        verification.scores_notified_at = datetime.datetime.now(datetime.timezone.utc)

        return

    # Every target reached on the teacher's overall average, which is what the
    # acta agreed on — but the same indicator can still be under the target in
    # a single subject, and that is the case this whole breakdown exists for.
    under = (
        db.query(ImprovementPlanVerificationCourseModel)
        .join(
            ImprovementPlanVerificationItemModel,
            ImprovementPlanVerificationItemModel.id
            == ImprovementPlanVerificationCourseModel.verification_item_id,
        )
        .filter(
            ImprovementPlanVerificationItemModel.verification_id == verification.id,
            ImprovementPlanVerificationCourseModel.met.is_(False),
        )
        .all()
    )

    if not under:
        return

    findings = [
        f"{row.course_name or 'asignatura sin nombre'}"
        f"{f' (Grupo {row.group_name})' if row.group_name else ''}: "
        f"{_indicator_label(row.item.target_type, row.item.target_ref)} en "
        f"{float(row.result_value):.2f} frente a la meta "
        f"{float(row.item.target_value):.2f}"
        for row in under
    ]
    message = (
        f"{teacher} alcanzó las metas del plan «{plan.title}»{where} en su "
        f"promedio general, pero sigue por debajo en "
        f"{len(under)} {'asignatura' if len(under) == 1 else 'asignaturas'}: "
        f"{_listed(findings)}."
    )
    _send(db, user_id, COURSE_ALERT_TITLE, message, link)
    verification.scores_notified_at = datetime.datetime.now(datetime.timezone.utc)


def _notify_comments(
    db, plan, verification, period_code: str | None, department_id: int | None
) -> None:
    """Tell the director when the complaint behind a qualitative commitment
    comes back at high risk."""

    if verification.comments_notified_at:
        return

    alerts = (
        db.query(ImprovementPlanVerificationCommentModel)
        .filter(
            ImprovementPlanVerificationCommentModel.verification_id
            == verification.id,
            ImprovementPlanVerificationCommentModel.is_alert.is_(True),
        )
        .all()
    )

    if not alerts:
        return

    user_id = _director_user_id(db, plan, department_id)

    if not user_id:
        return

    teacher = _teacher_name(db, plan.teacher_id)
    where = f" en {period_code}" if period_code else ""
    categories = sorted({row.category_name for row in alerts if row.category_name})
    about = f" sobre {', '.join(categories)}" if categories else ""

    message = (
        f"{teacher} tiene {len(alerts)} "
        f"{'comentario' if len(alerts) == 1 else 'comentarios'} de riesgo alto"
        f"{where}{about}, la misma observación que motivó el plan "
        f"«{plan.title}». Léelos antes de decidir si amerita un nuevo "
        f"acompañamiento."
    )

    _send(db, user_id, COMMENTS_ALERT_TITLE, message, manager_plan_path(plan.id))
    verification.comments_notified_at = datetime.datetime.now(datetime.timezone.utc)


# --------------------------------------------------------------------------- #
# Entry points, called by the evaluation processor                            #
# --------------------------------------------------------------------------- #
def score_threshold(db) -> float:
    """Institutional threshold an indicator counts as weak under. Used as the
    target of items the acta left without an explicit one."""

    setting = SettingsRepository(db).get_by_key(SCORE_THRESHOLD_SETTING)

    if not setting or setting.value is None:
        return DEFAULT_SCORE_THRESHOLD

    try:
        return float(setting.value)
    except (TypeError, ValueError):
        return DEFAULT_SCORE_THRESHOLD


def verify_scores_for_evaluation(db, evaluation) -> None:
    """Verify every plan this evaluation settles, as soon as its grades land.

    Hangs off the end of the processing and not off the AI analysis, which is
    triggered by hand: a director who never runs the analysis must still get
    the numbers verified.

    Best-effort, like every other alert here: a verification that fails must
    never undo an upload that succeeded.
    """

    period_id = getattr(evaluation, "academic_period_id", None)

    if not period_id:
        return

    try:
        plans = plans_to_verify(
            db, period_id, evaluated_teacher_ids(db, evaluation.id)
        )

        if not plans:
            return

        threshold = score_threshold(db)
        period = evaluation.academic_period
        period_code = period.code if period else None

        for plan in plans:
            verification = verify_plan_scores(
                db, plan, period_id, threshold, evaluation.id
            )

            if verification is None:
                continue

            _notify_scores(
                db, plan, verification, period_code, evaluation.department_id
            )
    except Exception as exc:
        logger.warning(
            "Failed to verify improvement plans for evaluation %s: %s",
            getattr(evaluation, "id", None),
            exc,
        )


def verify_comments_for_evaluation(db, evaluation) -> None:
    """Look for the complaints behind the qualitative commitments coming back.

    Only once the analysis has run: a comment carries no risk level nor
    pedagogical category until the AI has classified it.
    """

    period_id = getattr(evaluation, "academic_period_id", None)

    if not period_id:
        return

    try:
        plans = plans_to_verify(
            db, period_id, evaluated_teacher_ids(db, evaluation.id)
        )

        if not plans:
            return

        period = evaluation.academic_period
        period_code = period.code if period else None

        for plan in plans:
            verification = verify_plan_comments(db, plan, period_id, evaluation.id)

            if verification is None:
                continue

            _notify_comments(
                db, plan, verification, period_code, evaluation.department_id
            )
    except Exception as exc:
        logger.warning(
            "Failed to verify plan comments for evaluation %s: %s",
            getattr(evaluation, "id", None),
            exc,
        )
