"""
Database setup using SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from api.config import config


engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
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
