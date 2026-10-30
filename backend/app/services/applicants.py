"""Applicants: apply from the careers site, board listing, detail, stage moves, activity log."""

from pathlib import Path

from sqlmodel import Session, select

from app.integrations.cv import CvError, save_cv, upload_dir
from app.models import Activity, Applicant, Interview, Stage
from app.services import jobs
from app.services.errors import Conflict, Invalid, NotFound, fetch


def log(session: Session, applicant_id: int, message: str) -> None:
    """Add an activity line; the caller commits it together with the change it describes."""
    session.add(Activity(applicant_id=applicant_id, message=message))


def apply(session: Session, job_id: int, name: str, email: str, phone: str, filename: str, data: bytes) -> Applicant:
    jobs.open_job(session, job_id)
    duplicate = session.exec(select(Applicant).where(Applicant.job_id == job_id, Applicant.email == email)).first()
    if duplicate:
        raise Conflict("You have already applied for this job")
    try:
        stored, text = save_cv(filename, data)
    except CvError as e:
        raise Invalid(str(e)) from e
    applicant = Applicant(job_id=job_id, name=name.strip(), email=email, phone=phone.strip(),
                          cv_filename=filename or stored, cv_path=stored, cv_text=text)
    session.add(applicant)
    session.flush()
    log(session, applicant.id, "Applied through the careers site")
    session.commit()
    session.refresh(applicant)
    return applicant


def list_for_board(session: Session, job_id: int | None) -> list[dict]:
    query = select(Applicant).order_by(Applicant.created_at.desc())
    if job_id is not None:
        query = query.where(Applicant.job_id == job_id)
    # cv_text can be long; the board only needs the card fields.
    return [a.model_dump(exclude={"cv_text", "cv_path"}) for a in session.exec(query).all()]


def detail(session: Session, applicant_id: int) -> dict:
    applicant = fetch(session, Applicant, applicant_id)
    activity = session.exec(
        select(Activity).where(Activity.applicant_id == applicant_id).order_by(Activity.created_at, Activity.id)).all()
    interviews = session.exec(
        select(Interview).where(Interview.applicant_id == applicant_id).order_by(Interview.start)).all()
    return {**applicant.model_dump(exclude={"cv_path"}), "activity": activity, "interviews": interviews}


def move_stage(session: Session, applicant_id: int, stage: Stage) -> Applicant:
    applicant = fetch(session, Applicant, applicant_id)
    if applicant.stage != stage:
        log(session, applicant_id, f"Stage: {applicant.stage} → {stage}")
        applicant.stage = stage
        session.commit()
        session.refresh(applicant)
    return applicant


def cv_file(session: Session, applicant_id: int) -> tuple[Path, str]:
    """(path on disk, original filename) of the applicant's CV."""
    applicant = fetch(session, Applicant, applicant_id)
    if not applicant.cv_path:
        raise NotFound("No CV uploaded")
    return upload_dir() / applicant.cv_path, applicant.cv_filename
