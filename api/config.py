"""Configuration settings for the application."""

import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", "5000")
DATABASE_URL = os.getenv("DATABASE_URL")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

class Config:
    """Configuration class for the application."""

    PORT = int(PORT)
    ALLOWED_ORIGINS = ALLOWED_ORIGINS

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

config = Config()
