"""
Database setup using SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from api.config import config

database_url = config.SQLALCHEMY_DATABASE_URI

if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """
    Provide a database session
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
