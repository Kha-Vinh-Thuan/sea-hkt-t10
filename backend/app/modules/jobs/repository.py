"""Job queries. Only this file talks to the job table."""

from sqlmodel import Session, select

from app.modules.jobs.models import Job


def get(session: Session, job_id: int) -> Job | None:
    return session.get(Job, job_id)


def list_all(session: Session) -> list[Job]:
    return list(session.exec(select(Job).order_by(Job.created_at.desc())).all())


def list_open(session: Session) -> list[Job]:
    return list(session.exec(select(Job).where(Job.is_open).order_by(Job.created_at.desc())).all())


def save(session: Session, job: Job) -> Job:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
