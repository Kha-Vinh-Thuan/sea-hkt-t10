"""Interview table."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow


class Interview(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    interviewer_name: str = ""
    interviewer_email: str = Field(index=True)
    start: datetime = utc_field()
    end: datetime = utc_field()   # start + job.interview_duration_minutes
    location: str = ""            # meeting link or room
    created_at: datetime = utc_field(default_factory=utcnow)
