"""stored_file table: CV and attachment bytes kept in Postgres, so every dev machine sharing the DB can open them."""

from datetime import datetime

from sqlalchemy import Column, LargeBinary
from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow

class StoredFile(SQLModel, table=True):
    __tablename__ = "stored_file"

    # Random key like "3f9a...c1.pdf": same shape as the old file names on disk, so moved files keep their key.
    # Applicant.cv_path and ApplicantAttachment.stored_path hold this key.
    id: str = Field(primary_key=True)
    filename: str           # original name, shown to recruiters
    content_type: str       # from the checked extension, not the client
    size: int
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = utc_field(default_factory=utcnow)
