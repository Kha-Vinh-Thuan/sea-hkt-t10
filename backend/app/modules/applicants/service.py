"""Applicant rules: apply (open job, one application per email, valid CV), copy to another job, stage moves with
an activity log, recruiter edits (owners), refuse with a reason, archive / restore, extra attachments.
Candidate emails go through emails.py.
"""

from sqlmodel import Session

from app.integrations.cv import CvError, save_attachment, save_cv
from app.modules.applicants import emails, repository
from app.modules.files import repository as files
from app.modules.applicants.models import Applicant, ApplicantAttachment, RefuseReason, Source, Stage
from app.modules.applicants.schemas import ApplicantUpdate
from app.modules.interviews import repository as interview_repo
from app.modules.jobs import service as job_service
from app.modules.users import service as user_service
from app.utils.errors import Conflict, Invalid, NotFound
from app.utils.time import utcnow

MAX_INTRO = 2000
# The applicant withdrew: they get the "not interested" email instead of the refusal one.
WITHDRAWN_REASONS = {RefuseReason.refused_job_fit, RefuseReason.refused_salary}

def get(session: Session, applicant_id: int) -> Applicant:
    applicant = repository.get(session, applicant_id)
    if not applicant:
        raise NotFound("Applicant not found")
    return applicant

def _check_linkedin(url: str) -> str:
    url = url.strip()
    if url and not url.lower().startswith(("http://", "https://")):
        raise Invalid("LinkedIn must be an http(s) URL")
    return url

def apply(session: Session, job_id: int, name: str, email: str, phone: str, filename: str, data: bytes,
          linkedin: str = "", short_intro: str = "", source: Source = Source.careers_site) -> Applicant:
    job_service.get_open(session, job_id)
    linkedin = _check_linkedin(linkedin)
    if len(short_intro) > MAX_INTRO:
        raise Invalid(f"Short introduction must be at most {MAX_INTRO} characters")
    if repository.find_by_job_and_email(session, job_id, email):
        raise Conflict("You have already applied for this job")
    try:
        stored, text = save_cv(session, filename, data)
    except CvError as e:
        raise Invalid(str(e)) from e
    applicant = repository.add(session, Applicant(
        job_id=job_id, name=name.strip(), email=email, phone=phone.strip(), linkedin=linkedin,
        short_intro=short_intro.strip(), source=source, cv_filename=filename or stored, cv_path=stored, cv_text=text))
    repository.add_activity(session, applicant.id, "Applied through the careers site")
    session.commit()
    # Saved before emailing: the application stands even if the confirmation mail fails.
    emails.send(session, applicant, "Interest", "interest")
    session.commit()
    session.refresh(applicant)
    return applicant

def copy_to_job(session: Session, applicant_id: int, job_id: int) -> Applicant:
    """Odoo's action_job_add_applicants: same person, CV and source, fresh application in `new` for another job."""
    source = get(session, applicant_id)
    job = job_service.get(session, job_id)
    if repository.find_by_job_and_email(session, job_id, source.email):
        raise Conflict("This email has already applied for that job")
    # The CV is shared, not duplicated: both applicants point at the same stored_file key, and CVs are never deleted.
    copy = repository.add(session, Applicant(
        job_id=job_id, name=source.name, email=source.email, phone=source.phone, linkedin=source.linkedin,
        short_intro=source.short_intro, source=source.source, source_detail=source.source_detail,
        cv_filename=source.cv_filename, cv_path=source.cv_path, cv_text=source.cv_text))
    repository.add_activity(session, copy.id, f"Copied from {job_service.get(session, source.job_id).title}")
    repository.add_activity(session, source.id, f"Copied to {job.title}")
    session.commit()
    session.refresh(copy)
    return copy

def list_for_board(session: Session, job_id: int | None, archived: bool = False, q: str = "",
                   priority_min: int | None = None, tag: str = "", owner_id: int | None = None) -> list[dict]:
    # cv_text can be long (searched in SQL, not sent); the board only needs the card fields.
    applicants = repository.list_by_job(session, job_id, archived, q, priority_min, tag, owner_id)
    return [a.model_dump(exclude={"cv_text", "cv_path"}) for a in applicants]

def detail(session: Session, applicant_id: int) -> dict:
    applicant = get(session, applicant_id)
    return {
        **applicant.model_dump(exclude={"cv_path"}),
        "activity": repository.list_activity(session, applicant_id),
        "interviews": interview_repo.list_by_applicant(session, applicant_id),
        "other_applications": _other_applications(session, applicant),
        "attachments": [a.model_dump(exclude={"stored_path"}) for a in repository.list_attachments(session, applicant_id)],
    }

def _other_applications(session: Session, applicant: Applicant) -> list[dict]:
    # Odoo's application_count: the same person applying to other jobs (or re-applying after a refusal).
    return [{"id": a.id, "job_id": a.job_id, "job_title": job_service.get(session, a.job_id).title,
             "stage": a.stage, "archived": a.archived, "created_at": a.created_at}
            for a in repository.list_same_person(session, applicant)]

def change_stage(session: Session, applicant: Applicant, stage: Stage) -> None:
    """Move and log without committing, so callers can bundle it with their own change."""
    if applicant.stage != stage:
        repository.add_activity(session, applicant.id, f"Stage: {applicant.stage} → {stage}")
        applicant.stage = stage
        applicant.stage_changed_at = utcnow()
        applicant.hired_at = applicant.stage_changed_at if stage == Stage.hired else None

def move_stage(session: Session, applicant_id: int, stage: Stage) -> Applicant:
    applicant = get(session, applicant_id)
    if stage == Stage.rejected:
        raise Invalid("Use refuse to reject an applicant, so a reason is recorded")
    hired_now = stage == Stage.hired and applicant.stage != Stage.hired
    change_stage(session, applicant, stage)
    session.commit()
    if hired_now:
        emails.send(session, applicant, "Congratulations", "congratulations")
        session.commit()
    session.refresh(applicant)
    return applicant

def update(session: Session, applicant_id: int, data: ApplicantUpdate) -> Applicant:
    applicant = get(session, applicant_id)
    changes = data.model_dump(exclude_unset=True)
    if "linkedin" in changes:
        changes["linkedin"] = _check_linkedin(changes["linkedin"])
    for field in ("user_id", "next_action_user_id"):
        if changes.get(field) is not None and not user_service.get_active(session, changes[field]):
            raise Invalid("Owner must be an active user")
    if "tags" in changes:
        changes["tags"] = list(dict.fromkeys(t.strip() for t in changes["tags"] if t.strip()))  # dedupe, keep order
    changed = [field for field, value in changes.items() if getattr(applicant, field) != value]
    for field in changed:
        setattr(applicant, field, changes[field])
    if changed:
        # Field names only: notes may hold private remarks that should not be copied into the log.
        repository.add_activity(session, applicant.id, f"Updated: {', '.join(changed)}")
    session.commit()
    session.refresh(applicant)
    return applicant

def refuse(session: Session, applicant_id: int, reason: RefuseReason, send_email: bool) -> dict:
    applicant = get(session, applicant_id)
    change_stage(session, applicant, Stage.rejected)
    applicant.refuse_reason = reason
    applicant.refused_at = utcnow()
    repository.add_activity(session, applicant.id, f"Refused: {reason}")
    session.commit()
    emailed, mail_error = False, None
    if send_email:
        template = ("Not interested", "not_interested") if reason in WITHDRAWN_REASONS else ("Refusal", "refusal")
        emailed, mail_error = emails.send(session, applicant, *template)
        session.commit()
    session.refresh(applicant)
    return {"applicant": applicant.model_dump(exclude={"cv_text", "cv_path"}), "emailed": emailed, "mail_error": mail_error}

def compose_email(session: Session, applicant_id: int, template_id: int) -> dict:
    return emails.compose(session, get(session, applicant_id), template_id)

def send_email(session: Session, applicant_id: int, subject: str, body: str) -> dict:
    return emails.send_composed(session, get(session, applicant_id), subject, body)

def archive(session: Session, applicant_id: int) -> Applicant:
    applicant = get(session, applicant_id)
    if not applicant.archived:
        applicant.archived = True
        repository.add_activity(session, applicant.id, "Archived")
        session.commit()
        session.refresh(applicant)
    return applicant

def restore(session: Session, applicant_id: int) -> Applicant:
    """Odoo's reset_applicant: back on the board in the first stage, refusal forgotten."""
    applicant = get(session, applicant_id)
    applicant.archived = False
    applicant.refuse_reason = None
    applicant.refused_at = None
    change_stage(session, applicant, Stage.new)
    repository.add_activity(session, applicant.id, "Restored")
    session.commit()
    session.refresh(applicant)
    return applicant

def _file_bytes(session: Session, key: str) -> tuple[bytes, str]:
    stored = files.get(session, key)
    if not stored:  # an old disk name not moved yet: run `python -m app.move_uploads_to_db`
        raise NotFound("File not found")
    return stored.data, stored.content_type

def cv_file(session: Session, applicant_id: int) -> tuple[bytes, str, str]:
    """(bytes, original filename, content type) of the applicant's CV."""
    applicant = get(session, applicant_id)
    if not applicant.cv_path:
        raise NotFound("No CV uploaded")
    data, content_type = _file_bytes(session, applicant.cv_path)
    return data, applicant.cv_filename, content_type

def add_attachment(session: Session, applicant_id: int, filename: str, data: bytes) -> ApplicantAttachment:
    get(session, applicant_id)
    try:
        stored, content_type = save_attachment(session, filename, data)
    except CvError as e:
        raise Invalid(str(e)) from e
    attachment = ApplicantAttachment(applicant_id=applicant_id, filename=filename or stored, stored_path=stored,
                                     content_type=content_type, size=len(data))
    session.add(attachment)
    repository.add_activity(session, applicant_id, f"Attachment added: {attachment.filename}")
    session.commit()
    session.refresh(attachment)
    return attachment

def _attachment(session: Session, applicant_id: int, attachment_id: int) -> ApplicantAttachment:
    attachment = repository.get_attachment(session, applicant_id, attachment_id)
    if not attachment:
        raise NotFound("Attachment not found")
    return attachment

def attachment_file(session: Session, applicant_id: int, attachment_id: int) -> tuple[bytes, str, str]:
    """(bytes, original filename, content type) of one attachment."""
    attachment = _attachment(session, applicant_id, attachment_id)
    data, _ = _file_bytes(session, attachment.stored_path)
    return data, attachment.filename, attachment.content_type

def delete_attachment(session: Session, applicant_id: int, attachment_id: int) -> None:
    attachment = _attachment(session, applicant_id, attachment_id)
    session.delete(attachment)
    files.delete(session, attachment.stored_path)  # attachments are never shared, so the bytes go too
    repository.add_activity(session, applicant_id, f"Attachment deleted: {attachment.filename}")
    session.commit()
