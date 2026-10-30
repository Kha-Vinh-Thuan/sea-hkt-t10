"""Interview queries."""

from datetime import datetime

from sqlmodel import Session, select

from app.modules.applicants.models import Applicant
from app.modules.interviews.models import Interview
from app.modules.jobs.models import Job


def list_by_applicant(session: Session, applicant_id: int) -> list[Interview]:
    return list(session.exec(
        select(Interview).where(Interview.applicant_id == applicant_id).order_by(Interview.start)).all())


def find_clash(session: Session, interviewer_email: str, start: datetime, end: datetime) -> Interview | None:
    """Any interview of this interviewer overlapping [start, end)."""
    return session.exec(select(Interview).where(
        Interview.interviewer_email == interviewer_email, Interview.start < end, Interview.end > start)).first()


def list_upcoming(session: Session, now: datetime) -> list[tuple[Interview, Applicant, Job]]:
    return list(session.exec(
        select(Interview, Applicant, Job)
        .join(Applicant, Interview.applicant_id == Applicant.id)
        .join(Job, Applicant.job_id == Job.id)
        .where(Interview.end >= now)
        .order_by(Interview.start)
    ).all())


def add(session: Session, interview: Interview) -> Interview:
    session.add(interview)
    return interview
