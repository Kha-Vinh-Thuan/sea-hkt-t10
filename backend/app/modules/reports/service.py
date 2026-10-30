"""Recruitment summary per job (Odoo's simple reporting): counts by stage / source / refuse reason, hired vs openings,
average days from applying to being hired. Read-only, computed from applicants; no tables of its own.
"""

from collections import Counter
from enum import StrEnum

from sqlmodel import Session

from app.modules.applicants import repository as applicant_repo
from app.modules.applicants.models import Applicant, RefuseReason, Source, Stage
from app.modules.jobs import repository as job_repo
from app.modules.jobs import service as job_service
from app.utils.time import as_utc

def _counts(values: list[StrEnum], keys: type[StrEnum]) -> dict[str, int]:
    # Every key present (zero included) so the UI draws the same rows for every job.
    counter = Counter(values)
    return {key.value: counter[key] for key in keys}

def _avg_days_to_hire(applicants: list[Applicant]) -> float | None:
    days = [(as_utc(a.hired_at) - as_utc(a.created_at)).total_seconds() / 86_400 for a in applicants if a.hired_at]
    return round(sum(days) / len(days), 1) if days else None

def summary(session: Session, job_id: int | None = None) -> list[dict]:
    jobs = [job_service.get(session, job_id)] if job_id is not None else job_repo.list_all(session)
    by_job: dict[int, list[Applicant]] = {job.id: [] for job in jobs}
    for applicant in applicant_repo.list_for_jobs(session, list(by_job)):
        by_job[applicant.job_id].append(applicant)
    result = []
    for job in jobs:
        applicants = by_job[job.id]
        by_stage = _counts([a.stage for a in applicants], Stage)
        result.append({
            "job_id": job.id, "title": job.title, "is_open": job.is_open,
            "total": len(applicants),
            "by_stage": by_stage,
            "hired": by_stage[Stage.hired.value], "openings": job.openings,
            "avg_days_to_hire": _avg_days_to_hire(applicants),
            "by_source": _counts([a.source for a in applicants], Source),
            "refused_by_reason": _counts([a.refuse_reason for a in applicants if a.refuse_reason], RefuseReason),
        })
    return result
