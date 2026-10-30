"""Database tables: jobs, applicants, interviews, and an activity log per applicant."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_field(**kwargs: Any) -> Any:
    # timestamptz in Postgres, so the API returns "+00:00" and browsers show the right local time.
    return Field(sa_type=DateTime(timezone=True), **kwargs)


class Stage(StrEnum):
    # Fixed pipeline; order here is the column order on the board.
    new = "new"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    department: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    interview_duration_minutes: int = Field(default=45, gt=0)
    openings: int = Field(default=1, ge=0)
    is_open: bool = True
    created_at: datetime = utc_field(default_factory=utcnow)


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


class Interview(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    interviewer_name: str = ""
    interviewer_email: str = Field(index=True)
    start: datetime = utc_field()
    end: datetime = utc_field()   # start + job.interview_duration_minutes
    location: str = ""            # meeting link or room
    created_at: datetime = utc_field(default_factory=utcnow)


class Activity(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    message: str
    created_at: datetime = utc_field(default_factory=utcnow)
