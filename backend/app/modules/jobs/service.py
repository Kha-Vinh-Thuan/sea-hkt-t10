"""Job rules: only jobs accepting applications reach the public, valid ranges, counts for the recruiter list."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.modules.applicants import repository as applicant_repo
from app.modules.applicants.models import Stage
from app.modules.jobs import repository
from app.modules.jobs.models import Job
from app.modules.jobs.schemas import JobIn
from app.utils.errors import Invalid, NotFound


def today() -> date:
    # Company-local day: a job closing on the 31st stays open until midnight in Vietnam, not in UTC.
    return datetime.now(ZoneInfo(settings.timezone_name())).date()


def is_accepting(job: Job, on: date) -> bool:
    """Published and inside the [opens_on, closes_on] window; a missing date means no bound."""
    return (job.is_open
            and (job.opens_on is None or job.opens_on <= on)
            and (job.closes_on is None or on <= job.closes_on))


def get(session: Session, job_id: int) -> Job:
    job = repository.get(session, job_id)
    if not job:
        raise NotFound("Job not found")
    return job


def get_open(session: Session, job_id: int) -> Job:
    """A job visible on the careers site; closed or out-of-window jobs look like missing ones."""
    job = get(session, job_id)
    if not is_accepting(job, today()):
        raise NotFound("Job not found")
    return job


def list_open(session: Session) -> list[Job]:
    on = today()
    return [job for job in repository.list_open(session) if is_accepting(job, on)]


def list_with_counts(session: Session) -> list[dict]:
    counts = applicant_repo.count_by_job(session)
    hired = applicant_repo.count_by_job(session, Stage.hired)
    return [{**job.model_dump(), "applicant_count": counts.get(job.id, 0), "hired_count": hired.get(job.id, 0)}
            for job in repository.list_all(session)]


def check_ranges(data: JobIn) -> None:
    if data.opens_on and data.closes_on and data.closes_on < data.opens_on:
        raise Invalid("Closing date must be on or after the opening date")
    if data.salary_min is not None and data.salary_max is not None and data.salary_max < data.salary_min:
        raise Invalid("Maximum salary must be at least the minimum salary")


def create(session: Session, data: JobIn) -> Job:
    check_ranges(data)
    return repository.save(session, Job.model_validate(data))


def update(session: Session, job_id: int, data: JobIn) -> Job:
    check_ranges(data)
    job = get(session, job_id)
    job.sqlmodel_update(data.model_dump())
    return repository.save(session, job)
