"""All environment settings in one place. Read at call time, so tests can change env with monkeypatch."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///hr.db")
    # Neon / Supabase hand out postgres:// or postgresql:// URLs; SQLAlchemy would pick psycopg2, we ship psycopg 3.
    # Query params such as ?sslmode=require pass straight through to libpq.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def upload_dir() -> Path:
    path = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def timezone_name() -> str:
    return os.environ.get("TIMEZONE", "Asia/Ho_Chi_Minh")


def company_name() -> str:
    # The {company} placeholder in candidate emails.
    return os.environ.get("COMPANY_NAME", "Our company")


def secret_key() -> str:
    return os.environ.get("SECRET_KEY", "")


def recruiter_account() -> tuple[str, str]:
    return os.environ.get("RECRUITER_EMAIL", ""), os.environ.get("RECRUITER_PASSWORD", "")


def smtp() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "starttls": os.environ.get("SMTP_STARTTLS", "true").lower() == "true",
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "sender": os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER") or "hr@localhost",
    }


def frontend_url() -> str:
    # Links in candidate emails and the redirect after Google consent point here.
    return os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def google() -> dict:
    return {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback"),
    }
