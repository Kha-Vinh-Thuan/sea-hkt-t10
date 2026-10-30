"""Save an uploaded CV and extract its text. The apply form is public, so type and size are enforced here."""

import io
import os
import secrets
from pathlib import Path

from docx import Document
from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".pdf", ".docx", ".txt"}


class CvError(ValueError):
    pass


def upload_dir() -> Path:
    path = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_text(data: bytes, suffix: str) -> str:
    try:
        if suffix == ".pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages).strip()
        if suffix == ".docx":
            return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs).strip()
        return data.decode(errors="replace").strip()
    except Exception as e:  # noqa: BLE001 - any parser failure means the file is not a readable CV
        raise CvError("Could not read the CV file") from e


def save_cv(filename: str, data: bytes) -> tuple[str, str]:
    """Validate, store under a random name, return (stored_name, text)."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        raise CvError("CV must be a PDF, DOCX or TXT file")
    if not data:
        raise CvError("CV file is empty")
    if len(data) > MAX_BYTES:
        raise CvError("CV must be 5 MB or smaller")
    text = extract_text(data, suffix)
    stored = f"{secrets.token_hex(16)}{suffix}"
    (upload_dir() / stored).write_bytes(data)
    return stored, text
