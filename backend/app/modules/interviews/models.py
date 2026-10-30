"""Interview table, its lifecycle status and the recruiter's scorecard verdict."""

from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow

class InterviewStatus(StrEnum):
    scheduled = "scheduled"
    done = "done"
    no_show = "no_show"
    cancelled = "cancelled"

class Recommendation(StrEnum):
    hire = "hire"
    maybe = "maybe"
    no_hire = "no_hire"

class Interview(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    interviewer_name: str = ""
    interviewer_email: str = Field(index=True)
    start: datetime = utc_field()
    end: datetime = utc_field()   # start + job.interview_duration_minutes
    location: str = ""            # meeting link or room
    status: InterviewStatus = InterviewStatus.scheduled
    sequence: int = 0             # iCalendar SEQUENCE: bumped on every update so calendars replace the event
    score: int | None = None      # 1-5, set with feedback
    recommendation: Recommendation | None = None
    feedback: str = ""
    created_at: datetime = utc_field(default_factory=utcnow)
