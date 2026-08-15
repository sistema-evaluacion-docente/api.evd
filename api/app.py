"""
FastAPI EVD API
"""

import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import config
from api.core.middleware import ResponseEnvelopeMiddleware
from api.database import Base, engine
from api.exceptions import AppException
from api.exceptions.handlers import (
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from api.middlewares.dev_logs_middleware import DevLogsMiddleware
from api.models import (
    academic_group,
    academic_period,
    audit,
    comment,
    course,
    department,
    director,
    evaluation,
    evaluation_question_score,
    evaluation_score,
    faculty,
    improvement_plan,
    improvement_plan_case_report,
    improvement_plan_checkpoint,
    improvement_plan_checkpoint_note,
    improvement_plan_course,
    improvement_plan_document,
    improvement_plan_evidence,
    improvement_plan_evidence_comment,
    improvement_plan_evidence_request,
    improvement_plan_item,
    improvement_plan_item_comment,
    notification,
    role,
    setting,
    setting_history,
    teacher,
    user,
    user_role,
)
from api.routes import (
    academic_groups,
    academic_periods,
    audits,
    comments,
    courses,
    departments,
    directors,
    evaluation_question_scores,
    evaluation_scores,
    evaluations,
    faculties,
    health,
    improvement_plans,
    notifications,
    settings,
    stats,
    teachers,
    users,
    ws_dev_logs,
    ws_evaluations,
    ws_notifications,
)

_ = (
    academic_group,
    academic_period,
    audit,
    comment,
    course,
    department,
    director,
    evaluation,
    evaluation_question_score,
    evaluation_score,
    faculty,
    improvement_plan,
    improvement_plan_case_report,
    improvement_plan_checkpoint,
    improvement_plan_checkpoint_note,
    improvement_plan_course,
    improvement_plan_document,
    improvement_plan_evidence,
    improvement_plan_evidence_comment,
    improvement_plan_evidence_request,
    improvement_plan_item,
    improvement_plan_item_comment,
    role,
    teacher,
    user,
    user_role,
    setting,
    setting_history,
)

Base.metadata.create_all(bind=engine)


app = FastAPI(title="EVD API")

os.makedirs(config.UPLOAD_DIR, exist_ok=True)
# NOTE: UPLOAD_DIR is intentionally NOT mounted as a public static directory.
# Files under it (evaluation PDFs, improvement plan actas/evidencias) contain
# department/teacher-sensitive data and must be served through authenticated,
# permission-checked endpoints (see GET /evaluations/{id}/pdf).

_allow_all_origins = "*" in config.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if _allow_all_origins else config.ALLOWED_ORIGINS,
    allow_origin_regex=".*" if _allow_all_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ResponseEnvelopeMiddleware)
app.add_middleware(DevLogsMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(health.router)
app.include_router(teachers.router)
app.include_router(courses.router)
app.include_router(departments.router)
app.include_router(directors.router)
app.include_router(academic_groups.router)
app.include_router(evaluations.router)
app.include_router(evaluation_scores.router)
app.include_router(evaluation_question_scores.router)
app.include_router(comments.router)
app.include_router(academic_periods.router)
app.include_router(users.router)
app.include_router(audits.router)
app.include_router(faculties.router)
app.include_router(settings.router)
app.include_router(stats.router)
app.include_router(improvement_plans.router)
app.include_router(notifications.router)
app.include_router(ws_evaluations.router)
app.include_router(ws_dev_logs.router)
app.include_router(ws_notifications.router)
