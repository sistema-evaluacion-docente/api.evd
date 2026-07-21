"""
FastAPI EVD API
"""

import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    improvement_plan_checkpoint,
    improvement_plan_evidence,
    improvement_plan_item,
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
    settings,
    stats,
    teachers,
    users,
)
from api.routes import ws_evaluations, ws_dev_logs

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
    improvement_plan_checkpoint,
    improvement_plan_evidence,
    improvement_plan_item,
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
app.mount(
    f"/{config.UPLOAD_DIR}", StaticFiles(directory=config.UPLOAD_DIR), name="uploads"
)

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
app.include_router(ws_evaluations.router)
app.include_router(ws_dev_logs.router)
# app.include_router(admin_dashboard.router)
# app.include_router(improvement_plans.router)
# app.include_router(comparison.router)
