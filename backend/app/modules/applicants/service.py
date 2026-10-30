"""Applicant rules: apply (open job, one application per email, valid CV), stage moves with an activity log."""

from pathlib import Path

from sqlmodel import Session

from app.integrations.cv import CvError, cv_path, save_cv
from app.modules.applicants import repository
from app.modules.applicants.models import Applicant, Stage
from app.modules.interviews import repository as interview_repo
from app.modules.jobs import service as job_service
from app.utils.errors import Conflict, Invalid, NotFound


def get(session: Session, applicant_id: int) -> Applicant:
    applicant = repository.get(session, applicant_id)
    if not applicant:
        raise NotFound("Applicant not found")
    return applicant


def apply(session: Session, job_id: int, name: str, email: str, phone: str, filename: str, data: bytes) -> Applicant:
    job_service.get_open(session, job_id)
    if repository.find_by_job_and_email(session, job_id, email):
        raise Conflict("You have already applied for this job")
    try:
        stored, text = save_cv(filename, data)
    except CvError as e:
        raise Invalid(str(e)) from e
    applicant = repository.add(session, Applicant(
        job_id=job_id, name=name.strip(), email=email, phone=phone.strip(),
        cv_filename=filename or stored, cv_path=stored, cv_text=text))
    repository.add_activity(session, applicant.id, "Applied through the careers site")
    session.commit()
    session.refresh(applicant)
    return applicant


def list_for_board(session: Session, job_id: int | None) -> list[dict]:
    # cv_text can be long; the board only needs the card fields.
    return [a.model_dump(exclude={"cv_text", "cv_path"}) for a in repository.list_by_job(session, job_id)]


def detail(session: Session, applicant_id: int) -> dict:
    applicant = get(session, applicant_id)
    return {
        **applicant.model_dump(exclude={"cv_path"}),
        "activity": repository.list_activity(session, applicant_id),
        "interviews": interview_repo.list_by_applicant(session, applicant_id),
    }


def change_stage(session: Session, applicant: Applicant, stage: Stage) -> None:
    """Move and log without committing, so callers can bundle it with their own change."""
    if applicant.stage != stage:
        repository.add_activity(session, applicant.id, f"Stage: {applicant.stage} → {stage}")
        applicant.stage = stage


def move_stage(session: Session, applicant_id: int, stage: Stage) -> Applicant:
    applicant = get(session, applicant_id)
    change_stage(session, applicant, stage)
    session.commit()
    session.refresh(applicant)
    return applicant


def cv_file(session: Session, applicant_id: int) -> tuple[Path, str]:
    """(path on disk, original filename) of the applicant's CV."""
    applicant = get(session, applicant_id)
    if not applicant.cv_path:
        raise NotFound("No CV uploaded")
    return cv_path(applicant.cv_path), applicant.cv_filename
