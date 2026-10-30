"""Candidate emails (interest after apply, congratulations on hire, refusal). Texts live here as constants.

A mail failure never undoes the action that triggered it: it is logged on the applicant and reported back.
"""

from sqlmodel import Session

from app.integrations.mail import MailError, mail_configured, send_mail
from app.modules.applicants import repository
from app.modules.applicants.models import Applicant
from app.modules.jobs import service as job_service

INTEREST_SUBJECT = "We received your application for {job}"
INTEREST_BODY = (
    "Hello {name},\n\nThank you for applying for {job}. We received your application and will review it soon.\n"
    "We will contact you by email about the next steps.\n"
)
CONGRATULATIONS_SUBJECT = "Congratulations! Welcome aboard as {job}"
CONGRATULATIONS_BODY = (
    "Hello {name},\n\nCongratulations! We are happy to tell you that you have been selected for {job}.\n"
    "We will contact you shortly with the details about your first day.\n"
)
REFUSE_SUBJECT = "Your application for {job}"
REFUSE_BODY = (
    "Hello {name},\n\nThank you for your interest in {job} and for the time you spent applying.\n"
    "After careful consideration we have decided not to move forward with your application.\n"
    "We wish you all the best in your job search.\n"
)

def send(session: Session, applicant: Applicant, label: str, subject: str, body: str) -> tuple[bool, str | None]:
    """Send one templated email and log the outcome as activity (caller commits). Returns (emailed, error)."""
    job = job_service.get(session, applicant.job_id)
    values = {"name": applicant.name, "job": job.title}
    error = None
    if not mail_configured():
        error = "Email is not configured (SMTP_HOST)"
    else:
        try:
            send_mail([applicant.email], subject.format(**values), body.format(**values))
        except MailError as e:
            error = str(e)
    repository.add_activity(session, applicant.id, f"{label} email sent" if error is None else f"Email not sent: {error}")
    return error is None, error
