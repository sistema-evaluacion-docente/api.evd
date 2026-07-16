"""
FastAPI EVD API
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from api.config import config
from api.database import Base, engine
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
    pedagogical_category,
    risk_level,
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
    admin_dashboard,
    audits,
    comments,
    comparison,
    courses,
    departments,
    directors,
    evaluation_question_scores,
    evaluation_scores,
    evaluations,
    faculties,
    health,
    improvement_plans,
    settings,
    stats,
    teachers,
    users,
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

# "*" cannot be combined with allow_credentials=True (Starlette would then omit
# the Access-Control-Allow-Origin header on preflight). When a wildcard is
# configured, echo any origin via a regex instead so credentials keep working.
_allow_all_origins = "*" in config.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if _allow_all_origins else config.ALLOWED_ORIGINS,
    allow_origin_regex=".*" if _allow_all_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        response_body = exc.detail
    else:
        response_body = {
            "message": exc.detail,
            "error": exc.detail,
            "status": exc.status_code,
            "data": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return JSONResponse(status_code=exc.status_code, content=response_body)


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
app.include_router(admin_dashboard.router)
app.include_router(improvement_plans.router)
app.include_router(comparison.router)
