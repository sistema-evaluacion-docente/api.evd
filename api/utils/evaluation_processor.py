"""
Background processor for teacher evaluation PDFs.

Receives the already-parsed dict from parse_pdf so that the route can
validate period/department before queuing the task — no double-parsing.
"""

import asyncio
import logging
from urllib.parse import quote

from api.routes.ws_evaluations import manager as connection_manager
from api.core.websockets.events import EvaluationProgressEvent, EvaluationLogEvent
from api.database import SessionLocal
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.comment_pedagogical_category import CommentPedagogicalCategoryModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.models.role import RoleModel
from api.models.notification import NotificationModel
from api.models.director import DirectorsModel
from api.repositories.improvement_plans import ImprovementPlansRepository
from api.repositories.settings import SettingsRepository
from api.services.improvement_plan_service import (
    DEFAULT_SCORE_THRESHOLD,
    SCORE_THRESHOLD_SETTING,
)
from api.utils.plan_suggestion import suggestion_reasons
from api.utils.ai_analyzer import analyze_comment  # used by analyze_evaluation_comments
from api.core.websockets.events import NotificationEvent
from api.core.websockets.connection_manager import (
    connection_manager as notification_manager,
)

logger = logging.getLogger(__name__)

# id de RiskLevelModel para "ALTO" según el orden de inserción de
# scripts/seed_risk_categories.py (BAJO=1, MEDIO=2, ALTO=3).
HIGH_RISK_LEVEL_ID = 3

# Título de la alerta agregada de planes sugeridos. Se compara contra él para
# no repetir la alerta si el análisis se vuelve a correr.
PLAN_SUGGESTION_TITLE = "Docentes con plan de mejoramiento sugerido"

# Cuántos nombres caben en el mensaje antes de resumir con "y N más".
MAX_LISTED_TEACHERS = 5

# The PDF prints the contract type as a short code next to the teacher name;
# these are stored under the name the university uses for them. Codes without
# a known name (OTC, MTC) are stored as they come.
CONTRACT_TYPE_NAMES = {"TC": "Planta", "CT": "Catedra"}


def _contract_type_name(raw: str | None) -> str | None:
    """Translate the contract code parsed from the PDF into its stored name."""

    if not raw:
        return None

    return CONTRACT_TYPE_NAMES.get(raw.upper(), raw)


def _broadcast_progress(evaluation_id: int, stage: str, **kwargs) -> None:
    try:
        event = EvaluationProgressEvent(
            evaluation_id=evaluation_id,
            stage=stage,
            **kwargs,
        )

        try:
            asyncio.get_running_loop()

            asyncio.ensure_future(
                connection_manager.broadcast(f"eval:{evaluation_id}", event)
            )
        except RuntimeError:
            asyncio.run(connection_manager.broadcast(f"eval:{evaluation_id}", event))
    except Exception:
        logger.debug("Failed to broadcast WS progress for evaluation %d", evaluation_id)


def _broadcast_log(
    evaluation_id: int,
    level: str,
    message: str,
    teacher_name: str | None = None,
    teacher_code: str | None = None,
    course_name: str | None = None,
    course_code: str | None = None,
) -> None:
    """Broadcast a log message to all WebSocket clients connected to the evaluation channel."""

    try:
        event = EvaluationLogEvent(
            evaluation_id=evaluation_id,
            level=level,
            message=message,
            teacher_name=teacher_name,
            teacher_code=teacher_code,
            course_name=course_name,
            course_code=course_code,
        )

        try:
            asyncio.get_running_loop()

            asyncio.ensure_future(
                connection_manager.broadcast(f"eval:{evaluation_id}", event)
            )
        except RuntimeError:
            asyncio.run(connection_manager.broadcast(f"eval:{evaluation_id}", event))
    except Exception:
        logger.debug("Failed to broadcast WS log for evaluation %d", evaluation_id)


def _create_process_notification(
    db,
    evaluation_id: int,
    department_id: int | None,
    uploader_user_id: int | None,
    success: bool,
    teachers_count: int = 0,
) -> None:
    """
    Create notifications for the evaluation uploader
    and department director when evaluation processing finishes.
    """

    if success:
        title = "Evaluación procesada"
        message = f"""El procesamiento de la evaluación #{evaluation_id} finalizó exitosamente.
        Se procesaron {teachers_count} docentes."""
        notification_type = "success"
    else:
        title = "Error en procesamiento"
        message = f"""Ocurrió un error al procesar la evaluación #{evaluation_id}."""
        notification_type = "error"

    user_ids_to_notify: set[int] = set()

    if uploader_user_id:
        user_ids_to_notify.add(uploader_user_id)

    if department_id:
        director = (
            db.query(DirectorsModel)
            .filter(DirectorsModel.department_id == department_id)
            .first()
        )
        if director:
            user_ids_to_notify.add(director.user_id)

    for user_id in user_ids_to_notify:
        try:
            notification = NotificationModel(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
            )
            db.add(notification)
            db.flush()

            event = NotificationEvent(
                notification_id=notification.id,
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
            )

            channel = f"notifications:{user_id}"

            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(notification_manager.broadcast(channel, event))
            except RuntimeError:
                asyncio.run(notification_manager.broadcast(channel, event))

        except Exception as exc:
            logger.warning(
                "Failed to create/broadcast notification for user %d: %s",
                user_id,
                exc,
            )


def _create_analysis_notification(
    db,
    evaluation_id: int,
    department_id: int | None,
    uploader_user_id: int | None,
    success: bool,
    comments_count: int = 0,
) -> None:
    """
    Create notifications for the evaluation uploader
    and department director when AI analysis finishes.
    """

    if success:
        title = "Análisis IA completado"
        message = f"""El análisis de IA de la evaluación #{evaluation_id} finalizó exitosamente.
        Se procesaron {comments_count} comentarios."""
        notification_type = "success"
    else:
        title = "Error en análisis IA"
        message = f"""Ocurrió un error al procesar el análisis de IA
        de la evaluación #{evaluation_id}."""
        notification_type = "error"

    user_ids_to_notify: set[int] = set()

    if uploader_user_id:
        user_ids_to_notify.add(uploader_user_id)

    if department_id:
        director = (
            db.query(DirectorsModel)
            .filter(DirectorsModel.department_id == department_id)
            .first()
        )
        if director:
            user_ids_to_notify.add(director.user_id)

    for user_id in user_ids_to_notify:
        try:
            notification = NotificationModel(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
            )
            db.add(notification)
            db.flush()

            event = NotificationEvent(
                notification_id=notification.id,
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
            )

            channel = f"notifications:{user_id}"

            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(notification_manager.broadcast(channel, event))
            except RuntimeError:
                asyncio.run(notification_manager.broadcast(channel, event))

        except Exception as exc:
            logger.warning(
                "Failed to create/broadcast notification for user %d: %s",
                user_id,
                exc,
            )


def _create_high_risk_comment_notification(
    db,
    director_user_id: int,
    evaluation_id: int,
    teacher_name: str,
    comment: CommentModel,
    academic_period_name: str | None = None,
) -> None:
    """
    Create an alert notification for the department director when a
    comment is classified with the highest risk level (ALTO).
    """

    preview = (comment.original_text or "").strip()
    if len(preview) > 200:
        preview = preview[:200] + "..."

    title = "Alerta: comentario de riesgo alto"
    message = (
        f"Se detectó un comentario clasificado con riesgo ALTO para el "
        f"docente {teacher_name} en la evaluación #{evaluation_id}: "
        f'"{preview}"'
    )
    notification_type = "warning"

    link = None
    if comment.teacher_id:
        link = f"/docentes/{comment.teacher_id}"
        if academic_period_name:
            link += f"?period={quote(academic_period_name)}"

    try:
        notification = NotificationModel(
            user_id=director_user_id,
            title=title,
            message=message,
            type=notification_type,
            link=link,
        )
        db.add(notification)
        db.flush()

        event = NotificationEvent(
            notification_id=notification.id,
            user_id=director_user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )

        channel = f"notifications:{director_user_id}"

        try:
            asyncio.get_running_loop()
            asyncio.ensure_future(notification_manager.broadcast(channel, event))
        except RuntimeError:
            asyncio.run(notification_manager.broadcast(channel, event))

    except Exception as exc:
        logger.warning(
            "Failed to create/broadcast high-risk comment notification "
            "for user %d (comment %s): %s",
            director_user_id,
            comment.id,
            exc,
        )


def _run_async(coro):
    """Run a coroutine from this sync background task.

    The processor runs in a worker thread with no event loop of its own, so a
    private loop is opened just for the call and closed right after.
    """

    loop = asyncio.new_event_loop()

    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _score_threshold(db) -> float:
    """Institutional threshold an indicator counts as weak under."""

    setting = SettingsRepository(db).get_by_key(SCORE_THRESHOLD_SETTING)

    if not setting or setting.value is None:
        return DEFAULT_SCORE_THRESHOLD

    try:
        return float(setting.value)
    except (TypeError, ValueError):
        return DEFAULT_SCORE_THRESHOLD


def _plan_suggestion_message(
    suggested: list[dict], period_code: str | None, threshold: float
) -> str:
    """Body of the alert: who, and why, without opening the plan screen."""

    where = f" en {period_code}" if period_code else ""

    if len(suggested) == 1:
        teacher = suggested[0]
        reasons = ", ".join(suggestion_reasons(teacher))

        return (
            f"{teacher.get('name') or 'Un docente'} presenta resultados que "
            f"sugieren un plan de mejoramiento{where}: {reasons}. "
            f"El umbral institucional es {threshold}."
        )

    names = [teacher.get("name") or "Docente sin nombre" for teacher in suggested]
    listed = ", ".join(names[:MAX_LISTED_TEACHERS])
    rest = len(names) - MAX_LISTED_TEACHERS

    if rest > 0:
        listed += f" y {rest} más"

    return (
        f"{len(suggested)} docentes presentan resultados que sugieren un plan "
        f"de mejoramiento{where}: {listed}. "
        f"El umbral institucional es {threshold}."
    )


def _create_plan_suggestion_notification(db, evaluation) -> None:
    """Alert the director about the teachers an improvement plan is suggested
    for, once the evaluation has been analysed.

    One aggregated notification per evaluation and not one per teacher: a
    department has dozens of them and the bell would be unreadable. Teachers
    that already have a plan for the period are left out — the suggestion is
    already answered.

    Best-effort, like every other notification here: an alert that fails must
    never undo an analysis that succeeded.
    """

    department_id = evaluation.department_id
    period_id = evaluation.academic_period_id

    if not department_id or not period_id:
        return

    try:
        director = (
            db.query(DirectorsModel)
            .filter(DirectorsModel.department_id == department_id)
            .first()
        )

        if not director:
            return

        threshold = _score_threshold(db)

        candidates = _run_async(
            ImprovementPlansRepository(db).get_candidates(
                department_id=department_id,
                period_id=period_id,
                threshold=threshold,
                only_at_risk=True,
            )
        )

        if not candidates:
            return

        period_code = (
            evaluation.academic_period.code if evaluation.academic_period else None
        )

        link = "/planes/nuevo"
        if period_code:
            link += f"?period_code={quote(period_code)}"

        # Re-running the analysis of a period must not raise the same alert
        # twice; the director already has it in the bell.
        already_sent = (
            db.query(NotificationModel)
            .filter(
                NotificationModel.user_id == director.user_id,
                NotificationModel.title == PLAN_SUGGESTION_TITLE,
                NotificationModel.link == link,
            )
            .first()
        )

        if already_sent:
            return

        message = _plan_suggestion_message(candidates, period_code, threshold)

        notification = NotificationModel(
            user_id=director.user_id,
            title=PLAN_SUGGESTION_TITLE,
            message=message,
            type="warning",
            link=link,
        )
        db.add(notification)
        db.flush()

        event = NotificationEvent(
            notification_id=notification.id,
            user_id=director.user_id,
            title=PLAN_SUGGESTION_TITLE,
            message=message,
            notification_type="warning",
            link=link,
        )

        channel = f"notifications:{director.user_id}"

        try:
            asyncio.get_running_loop()
            asyncio.ensure_future(notification_manager.broadcast(channel, event))
        except RuntimeError:
            asyncio.run(notification_manager.broadcast(channel, event))

    except Exception as exc:
        logger.warning(
            "Failed to create plan suggestion notification for evaluation %s: %s",
            evaluation.id,
            exc,
        )


def process_evaluation(evaluation_id: int, parsed: dict) -> None:
    """Persist all data extracted from a teacher evaluation PDF.

    Designed to run as a FastAPI BackgroundTask. Opens its own DB session
    so the request session is already closed before this runs.

    On success:  evaluation.status = "COMPLETED", evaluation.count = # teachers
    On failure:  evaluation.status = "FAILED" (all other changes rolled back)
    """

    db = SessionLocal()

    _broadcast_log(
        evaluation_id,
        level="info",
        message="Iniciando procesamiento de la evaluación...",
    )

    try:
        period = (
            db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.code == parsed["period_code"])
            .first()
        )
        department = (
            db.query(DepartmentModel)
            .filter(DepartmentModel.code == parsed["department_code"])
            .first()
        )

        if not period or not department:
            raise ValueError(
                f"Period '{parsed['period_code']}' or department "
                f"'{parsed['department_code']}' not found"
            )

        _broadcast_log(
            evaluation_id,
            level="info",
            message=f"Procesando evaluación para periodo {period.name} y departamento {department.name}...",
        )

        for teacher_data in parsed["teachers"]:
            teacher_name = teacher_data["name"]
            teacher_code = teacher_data["code"]
            contract_type = _contract_type_name(teacher_data.get("contract_type"))

            user = (
                db.query(UserModel)
                .filter(UserModel.institutional_code == teacher_code)
                .first()
            )

            if not user:
                user = UserModel(
                    email=f"{teacher_code}@temp.local",
                    name=teacher_name,
                    institutional_code=teacher_code,
                    active=True,
                )
                db.add(user)
                db.flush()

                # Assign DOCENTE role to the new user
                docente_role = (
                    db.query(RoleModel).filter(RoleModel.name == "DOCENTE").first()
                )

                if docente_role:
                    user_role = UserRoleModel(user_id=user.id, role_id=docente_role.id)
                    db.add(user_role)
                    db.flush()

                _broadcast_log(
                    evaluation_id,
                    level="success",
                    message=f"Usuario creado: {teacher_name}",
                    teacher_name=teacher_name,
                    teacher_code=teacher_code,
                )
            else:
                # Sync the canonical name from the PDF; the parser already
                # strips any contract-type token, so this also heals stale
                # records where the token was incorrectly stored in the name.
                if user.name != teacher_name:
                    user.name = teacher_name

            teacher = (
                db.query(TeacherModel).filter(TeacherModel.user_id == user.id).first()
            )

            if not teacher:
                teacher = TeacherModel(
                    user_id=user.id,
                    department_id=department.id,
                    contract_type=contract_type,
                    active=True,
                )
                db.add(teacher)
                db.flush()
                _broadcast_log(
                    evaluation_id,
                    level="success",
                    message=f"Docente registrado: {teacher_name}",
                    teacher_name=teacher_name,
                    teacher_code=teacher_code,
                )
            else:
                if contract_type and teacher.contract_type != contract_type:
                    teacher.contract_type = contract_type

            groups_count = 0
            comments_count = 0

            for group_data in teacher_data.get("groups", []):
                course_code = group_data["course_code"]
                course_name = group_data["course_name"]

                course = (
                    db.query(CourseModel)
                    .filter(CourseModel.code == course_code)
                    .first()
                )

                if not course:
                    course = CourseModel(
                        code=course_code,
                        name=course_name,
                        department_id=department.id,
                    )
                    db.add(course)
                    db.flush()
                    _broadcast_log(
                        evaluation_id,
                        level="info",
                        message=f"Materia creada: {course_name}",
                        teacher_name=teacher_name,
                        teacher_code=teacher_code,
                        course_name=course_name,
                        course_code=course_code,
                    )

                group_name = f"{group_data['group']}{group_data['section']}"
                academic_group = (
                    db.query(AcademicGroupModel)
                    .filter(
                        AcademicGroupModel.course_id == course.id,
                        AcademicGroupModel.teacher_id == teacher.id,
                        AcademicGroupModel.academic_period_id == period.id,
                        AcademicGroupModel.group_name == group_name,
                    )
                    .first()
                )

                if not academic_group:
                    academic_group = AcademicGroupModel(
                        course_id=course.id,
                        teacher_id=teacher.id,
                        academic_period_id=period.id,
                        group_name=group_name,
                    )
                    db.add(academic_group)
                    db.flush()

                eval_score = EvaluationScoreModel(
                    evaluation_id=evaluation_id,
                    academic_group_id=academic_group.id,
                    respondent_count=group_data["respondent_count"],
                    overall_average=group_data["overall_average"],
                )

                db.add(eval_score)
                db.flush()
                groups_count += 1

                for q_code, score in group_data["question_scores"].items():
                    if score is not None:
                        db.add(
                            EvaluationQuestionScoreModel(
                                evaluation_score_id=eval_score.id,
                                question_code=q_code,
                                score=score,
                            )
                        )

                group_comments = group_data.get("comments", [])

                for text in group_comments:
                    db.add(
                        CommentModel(
                            teacher_id=teacher.id,
                            evaluation_id=evaluation_id,
                            academic_groups_id=academic_group.id,
                            original_text=text,
                            risk_level=None,
                        )
                    )
                comments_count += len(group_comments)

            _broadcast_log(
                evaluation_id,
                level="success",
                message=f"Notas creadas para {teacher_name}: {groups_count} grupos, {comments_count} comentarios",
                teacher_name=teacher_name,
                teacher_code=teacher_code,
            )

        evaluation = (
            db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if evaluation:
            evaluation.status = "COMPLETED"
            evaluation.count = len(parsed["teachers"])
            evaluation.ai_status = "PENDING"

        db.commit()

        _broadcast_log(
            evaluation_id,
            level="success",
            message=f"Procesamiento completado: {len(parsed['teachers'])} docentes procesados",
        )

        _broadcast_progress(
            evaluation_id,
            stage="UPLOADING",
            status="COMPLETED",
            ai_status="PENDING",
            count=len(parsed["teachers"]),
        )

        _create_process_notification(
            db,
            evaluation_id=evaluation_id,
            department_id=department.id,
            uploader_user_id=evaluation.user_id if evaluation else None,
            success=True,
            teachers_count=len(parsed["teachers"]),
        )

        db.commit()

        logger.info("Evaluation %d processed successfully", evaluation_id)

    except Exception as exc:
        db.rollback()
        logger.error(
            "Failed to process evaluation %d: %s", evaluation_id, exc, exc_info=True
        )

        _broadcast_log(
            evaluation_id,
            level="error",
            message=f"Error al procesar la evaluación: {str(exc)}",
        )

        try:
            evaluation = (
                db.query(EvaluationModel)
                .filter(EvaluationModel.id == evaluation_id)
                .first()
            )

            if evaluation:
                evaluation.status = "FAILED"
                db.commit()

                _broadcast_progress(
                    evaluation_id,
                    stage="UPLOADING",
                    status="FAILED",
                )

                _create_process_notification(
                    db,
                    evaluation_id=evaluation_id,
                    department_id=evaluation.department_id,
                    uploader_user_id=evaluation.user_id,
                    success=False,
                )

                db.commit()
        except Exception:
            pass

    finally:
        db.close()


# TODO: optimize
def analyze_evaluation_comments(evaluation_id: int) -> None:
    """Run AI classification on every comment of an evaluation.

    Designed to run as a FastAPI BackgroundTask. Marks ai_status as
    ANALYZING while running, then ANALYZED on success or FAILED on error.
    """
    db = SessionLocal()

    _broadcast_log(
        evaluation_id,
        level="info",
        message=f"Iniciando análisis de comentarios con IA",
    )

    try:
        evaluation = (
            db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        if not evaluation:
            logger.error(
                "analyze_evaluation_comments: evaluation %d not found", evaluation_id
            )
            return

        evaluation.ai_status = "ANALYZING"
        db.commit()

        _broadcast_progress(
            evaluation_id,
            stage="ANALYZING",
            ai_status="ANALYZING",
        )

        _broadcast_log(
            evaluation_id,
            level="info",
            message="Analizando comentarios con IA...",
        )

        comments = (
            db.query(CommentModel)
            .filter(CommentModel.evaluation_id == evaluation_id)
            .all()
        )

        _broadcast_log(
            evaluation_id,
            level="info",
            message=f"Analizando {len(comments)} comentarios...",
        )

        risk_cache: dict[str, int | None] = {}
        category_cache: dict[str, int | None] = {}

        all_risk_levels = db.query(RiskLevelModel).all()
        risk_name_to_id: dict[str, int] = {
            r.name.lower(): r.id for r in all_risk_levels
        }

        all_categories = db.query(PedagogicalCategoryModel).all()
        category_name_to_id: dict[str, int] = {
            c.name.lower(): c.id for c in all_categories
        }

        director = (
            db.query(DirectorsModel)
            .filter(DirectorsModel.department_id == evaluation.department_id)
            .first()
        )
        director_user_id = director.user_id if director else None
        teacher_name_cache: dict[int, str] = {}

        analyzed_count = 0

        for comment in comments:
            if not comment.original_text:
                continue

            result = analyze_comment(comment.original_text)
            risk_label = result.get("risk_label")

            if risk_label is not None:
                if risk_label not in risk_cache:
                    risk_cache[risk_label] = risk_name_to_id.get(risk_label.lower())

                comment.risk_level = risk_cache[risk_label]
                comment.risk_score = result.get("risk_score")
                comment.risk_level_ai_model = result.get("risk_model")

                if comment.risk_level == HIGH_RISK_LEVEL_ID and director_user_id:
                    if comment.teacher_id not in teacher_name_cache:
                        teacher = (
                            db.query(TeacherModel)
                            .filter(TeacherModel.id == comment.teacher_id)
                            .first()
                        )
                        teacher_name_cache[comment.teacher_id] = (
                            teacher.user.name
                            if teacher and teacher.user
                            else "Docente desconocido"
                        )

                    _create_high_risk_comment_notification(
                        db,
                        director_user_id=director_user_id,
                        evaluation_id=evaluation_id,
                        teacher_name=teacher_name_cache[comment.teacher_id],
                        comment=comment,
                        academic_period_name=(
                            evaluation.academic_period.name
                            if evaluation.academic_period
                            else None
                        ),
                    )

            category_labels = result.get("category_labels", [])

            if category_labels:
                comment.pedagogical_category_ai_model = result.get("category_model")

            for category in category_labels:
                category_label = category["label"]

                if category_label not in category_cache:
                    category_cache[category_label] = category_name_to_id.get(
                        category_label.lower()
                    )

                category_id = category_cache[category_label]

                if category_id is not None:
                    db.add(
                        CommentPedagogicalCategoryModel(
                            comment_id=comment.id,
                            pedagogical_category_id=category_id,
                            score=category["score"],
                        )
                    )

            analyzed_count += 1

            if analyzed_count % 5 == 0:
                db.commit()
                _broadcast_log(
                    evaluation_id,
                    level="info",
                    message=f"Progreso: {analyzed_count}/{len(comments)} comentarios analizados",
                )

        db.commit()
        evaluation.ai_status = "ANALYZED"
        db.commit()

        _broadcast_log(
            evaluation_id,
            level="success",
            message=f"Análisis completado: {analyzed_count} comentarios procesados",
        )

        _broadcast_progress(
            evaluation_id,
            stage="ANALYZING",
            status="COMPLETED",
            ai_status="ANALYZED",
        )

        _create_analysis_notification(
            db,
            evaluation_id=evaluation_id,
            department_id=evaluation.department_id,
            uploader_user_id=evaluation.user_id,
            success=True,
            comments_count=analyzed_count,
        )

        # Only once the comments are classified: the suggestion also reads the
        # high-risk ones, which do not exist until the analysis has run.
        _create_plan_suggestion_notification(db, evaluation)

        db.commit()

        logger.info("AI analysis completed for evaluation %d", evaluation_id)

    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass

        logger.error(
            "AI analysis failed for evaluation %d: %s",
            evaluation_id,
            exc,
            exc_info=True,
        )

        _broadcast_log(
            evaluation_id,
            level="error",
            message=f"Error en el análisis de IA: {str(exc)}",
        )

        try:
            db.close()
            db = SessionLocal()
            evaluation = (
                db.query(EvaluationModel)
                .filter(EvaluationModel.id == evaluation_id)
                .first()
            )

            if evaluation:
                evaluation.ai_status = "FAILED"
                db.commit()

                _broadcast_progress(
                    evaluation_id,
                    stage="ANALYZING",
                    ai_status="FAILED",
                )

                _create_analysis_notification(
                    db,
                    evaluation_id=evaluation_id,
                    department_id=evaluation.department_id,
                    uploader_user_id=evaluation.user_id,
                    success=False,
                )

                db.commit()
        except Exception:
            pass

    finally:
        db.close()
