"""Save an uploaded CV (and extract its text) or an extra applicant attachment. Type and size are enforced here."""

import io
import secrets
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.config import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".pdf", ".docx", ".txt"}
# Extra applicant attachments: extension -> content type sent back on download (never the client's claim).
ATTACHMENT_TYPES = {
    ".pdf": "application/pdf", ".txt": "text/plain", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class CvError(ValueError):
    pass


def extract_text(data: bytes, suffix: str) -> str:
    try:
        if suffix == ".pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages).strip()
        if suffix == ".docx":
            return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs).strip()
        return data.decode(errors="replace").strip()
    except Exception as e:  # noqa: BLE001 - any parser failure means the file is not a readable CV
        raise CvError("Could not read the CV file") from e


def _check(filename: str, data: bytes, allowed: set[str], kind: str, types: str) -> str:
    """Validate type and size; returns the lowercase extension."""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise CvError(f"{kind} must be a {types} file")
    if not data:
        raise CvError(f"{kind} file is empty")
    if len(data) > MAX_BYTES:
        raise CvError(f"{kind} must be 5 MB or smaller")
    return suffix

def _write(data: bytes, suffix: str) -> str:
    stored = f"{secrets.token_hex(16)}{suffix}"
    (settings.upload_dir() / stored).write_bytes(data)
    return stored

def save_cv(filename: str, data: bytes) -> tuple[str, str]:
    """Validate, store under a random name, return (stored_name, text)."""
    suffix = _check(filename, data, ALLOWED, "CV", "PDF, DOCX or TXT")
    text = extract_text(data, suffix)
    return _write(data, suffix), text

def save_attachment(filename: str, data: bytes) -> tuple[str, str]:
    """Validate, store under a random name, return (stored_name, content_type)."""
    suffix = _check(filename, data, set(ATTACHMENT_TYPES), "Attachment", "PDF, DOCX, TXT, PNG or JPG")
    return _write(data, suffix), ATTACHMENT_TYPES[suffix]

def delete_file(stored: str) -> None:
    (settings.upload_dir() / stored).unlink(missing_ok=True)

def cv_path(stored: str) -> Path:
    return settings.upload_dir() / stored
