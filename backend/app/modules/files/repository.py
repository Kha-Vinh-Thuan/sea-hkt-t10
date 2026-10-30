"""stored_file queries. Writes are added to the session; the caller commits (file row and its reference together)."""

import secrets

from sqlmodel import Session

from app.modules.files.models import StoredFile

def add(session: Session, filename: str, content_type: str, data: bytes, suffix: str) -> str:
    """Stage a new file row; returns its key."""
    key = f"{secrets.token_hex(16)}{suffix}"
    session.add(StoredFile(id=key, filename=filename or key, content_type=content_type, size=len(data), data=data))
    return key

def get(session: Session, key: str) -> StoredFile | None:
    return session.get(StoredFile, key)

def delete(session: Session, key: str) -> None:
    stored = session.get(StoredFile, key)
    if stored:
        session.delete(stored)
