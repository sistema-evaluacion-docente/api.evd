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
from api.models.teacher import TeacherModel

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

        db.commit()
        logger.info("Evaluation %d processed successfully", evaluation_id)

    except Exception as exc:
        db.rollback()
        logger.error("Failed to process evaluation %d: %s", evaluation_id, exc, exc_info=True)

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
