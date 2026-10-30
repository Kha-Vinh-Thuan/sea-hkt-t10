"""Interview table, its lifecycle status and the recruiter's scorecard verdict."""

import secrets
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

class CandidateResponse(StrEnum):
    none = "none"
    accepted = "accepted"
    declined = "declined"

def new_token() -> str:
    return secrets.token_urlsafe(24)

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
    google_event_id: str = ""     # event on the interviewer's Google Calendar, "" = not synced
    meet_url: str = ""
    # Secret in the candidate's Accept / Decline links (no login): whoever has the email can answer.
    response_token: str = Field(default_factory=new_token, unique=True, index=True)
    candidate_response: CandidateResponse = CandidateResponse.none
    created_at: datetime = utc_field(default_factory=utcnow)
