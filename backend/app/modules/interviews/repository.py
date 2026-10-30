"""Interview queries. Cancelled interviews free their slot, so clash and upcoming queries skip them."""

from datetime import datetime

from sqlmodel import Session, func, select

from app.modules.applicants.models import Applicant
from app.modules.interviews.models import Interview, InterviewStatus
from app.modules.jobs.models import Job

def get(session: Session, interview_id: int) -> Interview | None:
    return session.get(Interview, interview_id)

def list_by_applicant(session: Session, applicant_id: int) -> list[Interview]:
    return list(session.exec(
        select(Interview).where(Interview.applicant_id == applicant_id).order_by(Interview.start)).all())

def find_clash(session: Session, interviewer_email: str, start: datetime, end: datetime,
               exclude_id: int | None = None) -> Interview | None:
    """Any active interview of this interviewer overlapping [start, end), other than `exclude_id`."""
    query = select(Interview).where(
        Interview.interviewer_email == interviewer_email, Interview.start < end, Interview.end > start,
        Interview.status != InterviewStatus.cancelled)
    if exclude_id is not None:
        query = query.where(Interview.id != exclude_id)
    return session.exec(query).first()

def list_upcoming(session: Session, now: datetime | None,
                  interviewer_email: str | None = None) -> list[tuple[Interview, Applicant, Job]]:
    """Active interviews ending after `now` (None = also past ones), optionally of one interviewer."""
    query = (select(Interview, Applicant, Job)
             .join(Applicant, Interview.applicant_id == Applicant.id)
             .join(Job, Applicant.job_id == Job.id)
             .where(Interview.status != InterviewStatus.cancelled)
             .order_by(Interview.start))
    if now is not None:
        query = query.where(Interview.end >= now)
    if interviewer_email is not None:
        query = query.where(func.lower(Interview.interviewer_email) == interviewer_email.lower())
    return list(session.exec(query).all())

def add(session: Session, interview: Interview) -> Interview:
    session.add(interview)
    return interview
