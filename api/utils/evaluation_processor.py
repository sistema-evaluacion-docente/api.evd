"""
Background processor for teacher evaluation PDFs.

Receives the already-parsed dict from parse_pdf so that the route can
validate period/department before queuing the task — no double-parsing.
"""

import logging

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
from api.utils.ai_analyzer import analyze_comment  # used by analyze_evaluation_comments

logger = logging.getLogger(__name__)


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

        for teacher_data in parsed["teachers"]:
            teacher = (
                db.query(TeacherModel)
                .filter(TeacherModel.institutional_code == teacher_data["code"])
                .first()
            )
            if not teacher:
                teacher = TeacherModel(
                    institutional_code=teacher_data["code"],
                    department_id=department.id,
                    contract_type=teacher_data.get("contract_type"),
                    active=True,
                )
                db.add(teacher)
                db.flush()

            for group_data in teacher_data.get("groups", []):
                course = (
                    db.query(CourseModel)
                    .filter(CourseModel.code == group_data["course_code"])
                    .first()
                )
                if not course:
                    course = CourseModel(
                        code=group_data["course_code"],
                        name=group_data["course_name"],
                        department_id=department.id,
                    )
                    db.add(course)
                    db.flush()

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

                for q_code, score in group_data["question_scores"].items():
                    if score is not None:
                        db.add(
                            EvaluationQuestionScoreModel(
                                evaluation_score_id=eval_score.id,
                                question_code=q_code,
                                score=score,
                            )
                        )

                for text in group_data.get("comments", []):
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
        logger.info("Evaluation %d processed successfully", evaluation_id)

    except Exception as exc:
        db.rollback()
        logger.error(
            "Failed to process evaluation %d: %s", evaluation_id, exc, exc_info=True
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
            logger.error("analyze_evaluation_comments: evaluation %d not found", evaluation_id)
            return

        evaluation.ai_status = "ANALYZING"
        db.commit()

        comments = (
            db.query(CommentModel)
            .filter(CommentModel.evaluation_id == evaluation_id)
            .all()
        )

        risk_cache: dict[str, int | None] = {}
        category_cache: dict[str, int | None] = {}

        for comment in comments:
            if not comment.original_text:
                continue

            result = analyze_comment(comment.original_text)

            risk_label = result.get("risk_label")
            if risk_label is not None:
                if risk_label not in risk_cache:
                    row = db.query(RiskLevelModel).filter(RiskLevelModel.name == risk_label).first()
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

        evaluation.ai_status = "ANALYZED"
        db.commit()
        logger.info("AI analysis completed for evaluation %d", evaluation_id)

    except Exception as exc:
        db.rollback()
        logger.error(
            "AI analysis failed for evaluation %d: %s", evaluation_id, exc, exc_info=True
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
        except Exception:
            pass

    finally:
        db.close()
