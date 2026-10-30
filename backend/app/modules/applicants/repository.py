"""Applicant and activity queries. Writes are added to the session; the service decides when to commit."""

from collections import Counter

from sqlmodel import Session, select

from app.modules.applicants.models import Activity, Applicant, Stage


def get(session: Session, applicant_id: int) -> Applicant | None:
    return session.get(Applicant, applicant_id)


def find_by_job_and_email(session: Session, job_id: int, email: str) -> Applicant | None:
    return session.exec(select(Applicant).where(Applicant.job_id == job_id, Applicant.email == email)).first()


def list_by_job(session: Session, job_id: int | None, archived: bool = False) -> list[Applicant]:
    query = select(Applicant).where(Applicant.archived == archived).order_by(Applicant.created_at.desc())
    if job_id is not None:
        query = query.where(Applicant.job_id == job_id)
    return list(session.exec(query).all())


def count_by_job(session: Session, stage: Stage | None = None) -> dict[int, int]:
    query = select(Applicant.job_id)
    if stage is not None:
        query = query.where(Applicant.stage == stage)
    return dict(Counter(session.exec(query).all()))


def add(session: Session, applicant: Applicant) -> Applicant:
    session.add(applicant)
    session.flush()  # assigns the id so the activity row can reference it
    return applicant


def add_activity(session: Session, applicant_id: int, message: str) -> None:
    session.add(Activity(applicant_id=applicant_id, message=message))


def list_activity(session: Session, applicant_id: int) -> list[Activity]:
    query = select(Activity).where(Activity.applicant_id == applicant_id).order_by(Activity.created_at, Activity.id)
    return list(session.exec(query).all())
