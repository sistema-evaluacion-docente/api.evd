"""
FastAPI EVD API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import Base, engine
from api.routes import health, users
from api.config import config


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
