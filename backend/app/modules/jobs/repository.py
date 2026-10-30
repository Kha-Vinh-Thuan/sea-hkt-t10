"""Job queries. Only this file talks to the job table."""

from sqlmodel import Session, select

from app.modules.jobs.models import Job, JobInterviewer


def get(session: Session, job_id: int) -> Job | None:
    return session.get(Job, job_id)


def list_all(session: Session) -> list[Job]:
    return list(session.exec(select(Job).order_by(Job.created_at.desc())).all())


def list_open(session: Session) -> list[Job]:
    return list(session.exec(select(Job).where(Job.is_open).order_by(Job.created_at.desc())).all())


def interviewer_ids(session: Session) -> dict[int, list[int]]:
    """job_id -> user ids, for every job in one query."""
    result: dict[int, list[int]] = {}
    for link in session.exec(select(JobInterviewer).order_by(JobInterviewer.user_id)).all():
        result.setdefault(link.job_id, []).append(link.user_id)
    return result

def set_interviewers(session: Session, job_id: int, user_ids: list[int]) -> None:
    """Replace the job's interviewer list. Caller commits."""
    for link in session.exec(select(JobInterviewer).where(JobInterviewer.job_id == job_id)).all():
        session.delete(link)
    session.add_all(JobInterviewer(job_id=job_id, user_id=user_id) for user_id in user_ids)

def save(session: Session, job: Job) -> Job:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
