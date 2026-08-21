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


# Public base URL of the SPA, to turn a deep link into something clickable from
# outside the app (an email has no router to resolve "/mis-planes/7" against).
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "http://localhost:5173").strip().rstrip("/")

def _env(name: str, default: str = "") -> str:
    """A trimmed environment value.

    A trailing space in a .env line is invisible in an editor and travels all
    the way into the SMTP login, where it fails as a wrong username. Nothing
    here is ever meant to be padded, so it is trimmed once at the door.
    """

    return (os.getenv(name) or default).strip()


# Outgoing mail. Credentials never live in the repo: fill them in .env.
MAIL_ENABLED = _env("MAIL_ENABLED", "true").lower() in ("true", "1", "yes")
# "smtp" sends for real; "console" only logs the rendered message, which is what
# lets the app and the tests run without any credentials at all.
MAIL_BACKEND = _env("MAIL_BACKEND", "console").lower()

SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USER = _env("SMTP_USER")
# For Gmail this is a 16-character *app password*, not the account password.
# Google prints it in groups of four; the spaces are for reading, not for
# sending, so they come out here.
SMTP_PASSWORD = _env("SMTP_PASSWORD").replace(" ", "")
# STARTTLS on 587; port 465 speaks SSL from the first byte instead.
SMTP_USE_TLS = _env("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

MAIL_FROM = _env("MAIL_FROM") or SMTP_USER
MAIL_FROM_NAME = _env("MAIL_FROM_NAME", "Sistema de Evaluación Docente · UFPS")

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

    FRONTEND_URL = FRONTEND_URL

    MAIL_ENABLED = MAIL_ENABLED
    MAIL_BACKEND = MAIL_BACKEND
    SMTP_HOST = SMTP_HOST
    SMTP_PORT = SMTP_PORT
    SMTP_USER = SMTP_USER
    SMTP_PASSWORD = SMTP_PASSWORD
    SMTP_USE_TLS = SMTP_USE_TLS
    MAIL_FROM = MAIL_FROM
    MAIL_FROM_NAME = MAIL_FROM_NAME

    HUGGINGFACE_RISK_MODEL=HUGGINGFACE_RISK_MODEL
    HUGGINGFACE_CATEGORY_MODEL=HUGGINGFACE_CATEGORY_MODEL


config = Config()
