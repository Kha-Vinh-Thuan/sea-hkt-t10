"""Job positions: list with applicant counts, create, update, and the open-jobs view of the careers site."""

from sqlmodel import Session, select

from app.models import Applicant, Job
from app.schemas import JobIn
from app.services.errors import NotFound, fetch


def open_job(session: Session, job_id: int) -> Job:
    """A job visible on the careers site; closed jobs look like missing ones."""
    job = fetch(session, Job, job_id)
    if not job.is_open:
        raise NotFound("Job not found")
    return job


def list_open(session: Session) -> list[Job]:
    return list(session.exec(select(Job).where(Job.is_open).order_by(Job.created_at.desc())).all())


def list_with_counts(session: Session) -> list[dict]:
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    counts: dict[int, int] = {}
    for job_id in session.exec(select(Applicant.job_id)).all():
        counts[job_id] = counts.get(job_id, 0) + 1
    return [{**job.model_dump(), "applicant_count": counts.get(job.id, 0)} for job in jobs]


def create(session: Session, data: JobIn) -> Job:
    job = Job.model_validate(data)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update(session: Session, job_id: int, data: JobIn) -> Job:
    job = fetch(session, Job, job_id)
    job.sqlmodel_update(data.model_dump())
    session.commit()
    session.refresh(job)
    return job
