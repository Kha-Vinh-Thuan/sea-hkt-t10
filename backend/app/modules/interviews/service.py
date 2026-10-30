"""Interview rules: job length, no past times, no interviewer double booking, then email the .ics invite."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.integrations.mail import MailError, build_ics, mail_configured, mail_from, send_invite
from app.modules.applicants import repository as applicant_repo
from app.modules.applicants import service as applicant_service
from app.modules.applicants.models import Applicant, Stage
from app.modules.interviews import repository
from app.modules.interviews.models import Interview
from app.modules.interviews.schemas import InterviewIn
from app.modules.jobs import service as job_service
from app.modules.jobs.models import Job
from app.utils.errors import Conflict, Invalid
from app.utils.time import as_utc, utcnow

# Booking an interview moves early-stage applicants forward; later stages (offer, hired...) stay put.
STAGES_BEFORE_INTERVIEW = {Stage.new, Stage.screening}


def upcoming(session: Session) -> list[dict]:
    rows = repository.list_upcoming(session, utcnow())
    return [{**i.model_dump(), "applicant_name": a.name, "job_title": j.title} for i, a, j in rows]


def schedule(session: Session, applicant_id: int, data: InterviewIn) -> dict:
    applicant = applicant_service.get(session, applicant_id)
    job = job_service.get(session, applicant.job_id)
    start = as_utc(data.start)
    if start <= utcnow():
        raise Invalid("Interview time must be in the future")
    end = start + timedelta(minutes=job.interview_duration_minutes)
    if repository.find_clash(session, data.interviewer_email, start, end):
        raise Conflict("The interviewer already has an interview at that time")

    interview = repository.add(session, Interview(
        applicant_id=applicant_id, interviewer_name=data.interviewer_name.strip(),
        interviewer_email=data.interviewer_email, start=start, end=end, location=data.location.strip()))
    if applicant.stage in STAGES_BEFORE_INTERVIEW:
        applicant_service.change_stage(session, applicant, Stage.interview)
    when = start.astimezone(ZoneInfo(settings.timezone_name())).strftime("%a %d/%m/%Y %H:%M (%Z)")
    applicant_repo.add_activity(session, applicant_id,
                                f"Interview scheduled {when} with {data.interviewer_name or data.interviewer_email}")
    session.commit()
    session.refresh(interview)

    # Saved before emailing: a mail failure is reported, never loses the booking.
    emailed, mail_error = _send_invitation(applicant, job, interview, when)
    applicant_repo.add_activity(session, applicant_id,
                                "Invitation emailed" if emailed else f"Invitation not sent: {mail_error}")
    session.commit()
    session.refresh(interview)  # commit expires loaded objects; reload before serializing
    return {"interview": interview, "emailed": emailed, "mail_error": mail_error}


def _send_invitation(applicant: Applicant, job: Job, interview: Interview, when: str) -> tuple[bool, str | None]:
    if not mail_configured():
        return False, "Email is not configured (SMTP_HOST), invitation not sent"
    attendees = [applicant.email, interview.interviewer_email]
    summary = f"Interview: {applicant.name} - {job.title}"
    try:
        send_invite(
            to=attendees,
            subject=summary,
            body=(f"Hello {applicant.name},\n\nYour interview for {job.title} is scheduled for {when}, "
                  f"{job.interview_duration_minutes} minutes.\nLocation: {interview.location or 'to be confirmed'}"
                  "\n\nThe attached invitation adds it to your calendar.\n"),
            ics=build_ics(f"interview-{interview.id}@hr-system", summary, interview.start, interview.end,
                          interview.location, mail_from(), attendees),
        )
    except MailError as e:
        return False, str(e)
    return True, None
