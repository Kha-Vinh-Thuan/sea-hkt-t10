"""Job rules: closed jobs are invisible to the public, applicant counts for the recruiter list."""

from sqlmodel import Session

from app.modules.applicants import repository as applicant_repo
from app.modules.jobs import repository
from app.modules.jobs.models import Job
from app.modules.jobs.schemas import JobIn
from app.utils.errors import NotFound


def get(session: Session, job_id: int) -> Job:
    job = repository.get(session, job_id)
    if not job:
        raise NotFound("Job not found")
    return job


def get_open(session: Session, job_id: int) -> Job:
    """A job visible on the careers site; closed jobs look like missing ones."""
    job = get(session, job_id)
    if not job.is_open:
        raise NotFound("Job not found")
    return job


def list_open(session: Session) -> list[Job]:
    return repository.list_open(session)


def list_with_counts(session: Session) -> list[dict]:
    counts = applicant_repo.count_by_job(session)
    return [{**job.model_dump(), "applicant_count": counts.get(job.id, 0)} for job in repository.list_all(session)]


def create(session: Session, data: JobIn) -> Job:
    return repository.save(session, Job.model_validate(data))


def update(session: Session, job_id: int, data: JobIn) -> Job:
    job = get(session, job_id)
    job.sqlmodel_update(data.model_dump())
    return repository.save(session, job)
