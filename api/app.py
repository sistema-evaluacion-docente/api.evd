"""
FastAPI EVD API
"""

from datetime import datetime, timezone
from time import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
    evaluation,
    evaluation_question_score,
    evaluation_score,
    role,
    teacher,
    user,
    user_role,
)
from api.routes import academic_periods, audits, health, teachers, users

_ = (
    academic_group,
    academic_period,
    audit,
    comment,
    course,
    department,
    evaluation,
    evaluation_question_score,
    evaluation_score,
    role,
    teacher,
    user,
    user_role,
)

Base.metadata.create_all(bind=engine)


app = FastAPI(title="EVD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
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
app.include_router(academic_periods.router)
app.include_router(users.router)
app.include_router(audits.router)
