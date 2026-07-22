"""
Background processor for teacher evaluation PDFs.

Receives the already-parsed dict from parse_pdf so that the route can
validate period/department before queuing the task — no double-parsing.
"""

import asyncio
import logging

from api.routes.ws_evaluations import manager as connection_manager
from api.core.websockets.events import EvaluationProgressEvent, EvaluationLogEvent
from api.database import SessionLocal
from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.utils.ai_analyzer import analyze_comment  # used by analyze_evaluation_comments

logger = logging.getLogger(__name__)


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


def process_evaluation(evaluation_id: int, parsed: dict) -> None:
    """Persist all data extracted from a teacher evaluation PDF.

    Designed to run as a FastAPI BackgroundTask. Opens its own DB session
    so the request session is already closed before this runs.

    On success:  evaluation.status = "COMPLETED", evaluation.count = # teachers
    On failure:  evaluation.status = "FAILED" (all other changes rolled back)
    """
    db = SessionLocal()

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
            message=f"Iniciando procesamiento del período {period.code} - {department.name}",
        )

        for teacher_data in parsed["teachers"]:
            teacher_name = teacher_data["name"]
            teacher_code = teacher_data["code"]

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

                _broadcast_log(
                    evaluation_id,
                    level="success",
                    message=f"Usuario creado: {teacher_name}",
                    teacher_name=teacher_name,
                    teacher_code=teacher_code,
                )

            teacher = (
                db.query(TeacherModel).filter(TeacherModel.user_id == user.id).first()
            )

            if not teacher:
                teacher = TeacherModel(
                    user_id=user.id,
                    department_id=department.id,
                    contract_type=teacher_data.get("contract_type"),
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
                            pedagogical_category_id=None,
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
        except Exception:
            pass

    finally:
        db.close()


def analyze_evaluation_comments(evaluation_id: int) -> None:
    """Run AI classification on every comment of an evaluation.

    Designed to run as a FastAPI BackgroundTask. Marks ai_status as
    ANALYZING while running, then ANALYZED on success or FAILED on error.
    """
    db = SessionLocal()

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
            message="Iniciando análisis de comentarios con IA",
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

        analyzed_count = 0
        for comment in comments:
            if not comment.original_text:
                continue

            result = analyze_comment(comment.original_text)

            risk_label = result.get("risk_label")
            if risk_label is not None:
                if risk_label not in risk_cache:
                    row = (
                        db.query(RiskLevelModel)
                        .filter(RiskLevelModel.name == risk_label)
                        .first()
                    )
                    risk_cache[risk_label] = row.id if row else None
                comment.risk_level = risk_cache[risk_label]
                comment.risk_score = result.get("risk_score")

            category_label = result.get("category_label")
            if category_label is not None:
                if category_label not in category_cache:
                    row = (
                        db.query(PedagogicalCategoryModel)
                        .filter(PedagogicalCategoryModel.name == category_label)
                        .first()
                    )
                    category_cache[category_label] = row.id if row else None
                comment.pedagogical_category_id = category_cache[category_label]
                comment.category_score = result.get("category_score")

            analyzed_count += 1

            if analyzed_count % 10 == 0:
                _broadcast_log(
                    evaluation_id,
                    level="info",
                    message=f"Progreso: {analyzed_count}/{len(comments)} comentarios analizados",
                )

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
            ai_status="ANALYZED",
        )

        logger.info("AI analysis completed for evaluation %d", evaluation_id)

    except Exception as exc:
        db.rollback()
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
        except Exception:
            pass

    finally:
        db.close()
