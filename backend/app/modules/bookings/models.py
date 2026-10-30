"""Slot proposal: times a recruiter offered a candidate by email; the candidate picks one on a public page."""

from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.modules.interviews.models import new_token
from app.utils.time import utc_field, utcnow

PROPOSAL_TTL = timedelta(days=7)

class ProposalStatus(StrEnum):
    open = "open"
    booked = "booked"
    expired = "expired"

def _expiry() -> datetime:
    return utcnow() + PROPOSAL_TTL

class SlotProposal(SQLModel, table=True):
    __tablename__ = "slot_proposal"

    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(default_factory=new_token, unique=True, index=True)   # the secret in the booking link
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    interviewer_id: int = Field(foreign_key="app_user.id")
    slots: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))  # ISO UTC start times
    location: str = ""
    status: ProposalStatus = ProposalStatus.open
    created_at: datetime = utc_field(default_factory=utcnow)
    expires_at: datetime = utc_field(default_factory=_expiry)
