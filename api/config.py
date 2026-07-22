"""Configuration settings for the application."""

import os

from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", "5000")
DATABASE_URL = os.getenv("DATABASE_URL")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
# Comma-separated list of allowed CORS origins. Defaults to the local dev
# frontends. A literal "*" is supported but is handled specially in app.py
# because "*" is invalid together with allow_credentials=True.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if origin.strip()
]
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

FIREBASE_CREDENTIALS = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": (os.getenv("FIREBASE_PRIVATE_KEY") or "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
}


HUGGINGFACE_RISK_MODEL=os.getenv("HUGGINGFACE_RISK_MODEL")
HUGGINGFACE_CATEGORY_MODEL=os.getenv("HUGGINGFACE_CATEGORY_MODEL")


class Config:
    """Configuration class for the application."""

    PORT = int(PORT)
    DEBUG = DEBUG
    ALLOWED_ORIGINS = ALLOWED_ORIGINS

    FIREBASE_CREDENTIALS = FIREBASE_CREDENTIALS

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_DIR = UPLOAD_DIR
    MAX_UPLOAD_SIZE_MB = MAX_UPLOAD_SIZE_MB

    HUGGINGFACE_RISK_MODEL=HUGGINGFACE_RISK_MODEL
    HUGGINGFACE_CATEGORY_MODEL=HUGGINGFACE_CATEGORY_MODEL


config = Config()
