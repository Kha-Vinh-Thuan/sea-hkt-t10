"""Save an uploaded CV (and extract its text) or an extra applicant attachment as a stored_file row.
Type and size are enforced here.
"""

import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader
from sqlmodel import Session

from app.modules.files import repository as files

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

def save_cv(session: Session, filename: str, data: bytes) -> tuple[str, str]:
    """Validate, stage a stored_file row (caller commits), return (file key, text)."""
    suffix = _check(filename, data, ALLOWED, "CV", "PDF, DOCX or TXT")
    text = extract_text(data, suffix)
    return files.add(session, filename, ATTACHMENT_TYPES[suffix], data, suffix), text

def save_attachment(session: Session, filename: str, data: bytes) -> tuple[str, str]:
    """Validate, stage a stored_file row (caller commits), return (file key, content_type)."""
    suffix = _check(filename, data, set(ATTACHMENT_TYPES), "Attachment", "PDF, DOCX, TXT, PNG or JPG")
    return files.add(session, filename, ATTACHMENT_TYPES[suffix], data, suffix), ATTACHMENT_TYPES[suffix]
