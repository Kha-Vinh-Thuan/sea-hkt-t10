"""One-off: copy old CV / attachment files from UPLOAD_DIR into stored_file. Run: python -m app.move_uploads_to_db

Each row keeps the disk name as its key, so Applicant.cv_path / ApplicantAttachment.stored_path already point at it
and need no rewrite. Idempotent (keys already in the DB are skipped); files on disk are left alone.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.config.database import engine, migrate
from app.integrations.cv import ATTACHMENT_TYPES
from app.modules.applicants.models import Applicant, ApplicantAttachment
from app.modules.files.models import StoredFile

def move(session: Session, upload_dir: Path) -> dict[str, int]:
    """Insert every referenced file found on disk; returns counts (moved, already_in_db, missing_on_disk)."""
    references = {key: name for key, name in session.exec(select(Applicant.cv_path, Applicant.cv_filename)) if key}
    references.update(session.exec(select(ApplicantAttachment.stored_path, ApplicantAttachment.filename)).all())
    counts = {"moved": 0, "already_in_db": 0, "missing_on_disk": 0}
    for key, filename in references.items():
        path = upload_dir / key
        if session.get(StoredFile, key):
            counts["already_in_db"] += 1
        elif not path.is_file():
            counts["missing_on_disk"] += 1
        else:
            data = path.read_bytes()
            content_type = ATTACHMENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
            session.add(StoredFile(id=key, filename=filename or key, content_type=content_type, size=len(data),
                                   data=data))
            session.commit()  # one file per commit: a crash halfway keeps what was moved, a rerun finishes the rest
            counts["moved"] += 1
    return counts

if __name__ == "__main__":
    migrate()
    with Session(engine) as session:
        counts = move(session, settings.upload_dir())
    print(", ".join(f"{name}: {count}" for name, count in counts.items()))
