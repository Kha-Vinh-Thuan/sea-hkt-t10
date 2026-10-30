"""Candidate emails: the automatic ones (interest, congratulations, refusal, not interested) and the recruiter composer.

Texts live in the mail_template table (admin-editable, seeded from mail_templates/defaults.py).
A mail failure never undoes the action that triggered it: it is logged on the applicant and reported back.
"""

from sqlmodel import Session

from app.integrations.mail import MailError, mail_configured, send_mail
from app.modules.applicants import repository
from app.modules.applicants.models import Applicant
from app.modules.jobs import service as job_service
from app.modules.mail_templates import service as template_service

def _values(session: Session, applicant: Applicant) -> dict[str, str]:
    return template_service.placeholder_values(applicant.name, job_service.get(session, applicant.job_id).title)

def _deliver(applicant: Applicant, subject: str, body: str) -> str | None:
    """Send to the applicant; the error text instead of an exception."""
    if not mail_configured():
        return "Email is not configured (SMTP_HOST)"
    try:
        send_mail([applicant.email], subject, body)
    except MailError as e:
        return str(e)
    return None

def send(session: Session, applicant: Applicant, label: str, key: str) -> tuple[bool, str | None]:
    """Send the template `key` and log the outcome as activity (caller commits). Returns (emailed, error)."""
    values = _values(session, applicant)
    subject, body = template_service.texts_for_key(session, key)
    error = _deliver(applicant, template_service.render(subject, values), template_service.render(body, values))
    repository.add_activity(session, applicant.id, f"{label} email sent" if error is None else f"Email not sent: {error}")
    return error is None, error

def compose(session: Session, applicant: Applicant, template_id: int) -> dict:
    """A template rendered for this applicant, for the recruiter to edit before sending."""
    template = template_service.get(session, template_id)
    values = _values(session, applicant)
    return {"subject": template_service.render(template.subject, values),
            "body": template_service.render(template.body, values)}

def send_composed(session: Session, applicant: Applicant, subject: str, body: str) -> dict:
    """Send what the recruiter wrote (already final, not rendered again) and log subject + body. Commits."""
    error = _deliver(applicant, subject, body)
    repository.add_activity(session, applicant.id,
                            f"Email sent: {subject}\n\n{body}" if error is None else f"Email not sent: {subject}: {error}")
    session.commit()
    return {"sent": error is None, "error": error}
