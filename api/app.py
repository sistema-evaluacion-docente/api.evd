"""
FastAPI EVD API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import config
from api.database import Base, engine
from api.models import audit, department, role, user, user_role
from api.routes import audits, health, users

_ = (audit, department, role, user, user_role)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EVD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(users.router)
app.include_router(audits.router)
