"""All environment settings in one place. Read at call time, so tests can change env with monkeypatch."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///hr.db")


def upload_dir() -> Path:
    path = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def timezone_name() -> str:
    return os.environ.get("TIMEZONE", "Asia/Ho_Chi_Minh")


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
