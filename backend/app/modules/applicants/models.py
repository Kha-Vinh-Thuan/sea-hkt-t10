"""Applicant and activity-log tables, plus the fixed pipeline stages."""

from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow


class Stage(StrEnum):
    # Fixed pipeline; order here is the column order on the board.
    new = "new"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"


class Applicant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    name: str
    email: str = Field(index=True)
    phone: str = ""
    stage: Stage = Stage.new
    cv_filename: str = ""   # original name, shown to recruiters
    cv_path: str = ""       # random name on disk, never derived from user input
    cv_text: str = ""       # extracted text, read by recruiters and later by the Filter agent
    created_at: datetime = utc_field(default_factory=utcnow)


class Activity(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    message: str
    created_at: datetime = utc_field(default_factory=utcnow)
