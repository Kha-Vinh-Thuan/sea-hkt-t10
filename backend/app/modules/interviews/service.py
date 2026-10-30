"""Interview rules: book / reschedule / cancel (job length, no past times, no interviewer double booking,
email the .ics with a stable UID) and the post-interview scorecard."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.integrations.mail import MailError, build_ics, mail_configured, mail_from, send_invite
from app.modules.applicants import repository as applicant_repo
from app.modules.applicants import service as applicant_service
from app.modules.applicants.models import Applicant, Stage
from app.modules.interviews import repository
from app.modules.interviews.models import Interview, InterviewStatus
from app.modules.interviews.schemas import FeedbackIn, InterviewIn
from app.modules.jobs import service as job_service
from app.modules.jobs.models import Job
from app.modules.users.models import Role, User
from app.utils.errors import Conflict, Forbidden, Invalid, NotFound
from app.utils.time import as_utc, utcnow

# Booking an interview moves early-stage applicants forward; later stages (offer, hired...) stay put.
STAGES_BEFORE_INTERVIEW = {Stage.new, Stage.screening}

def upcoming(session: Session, user: User | None = None) -> list[dict]:
    """Staff (or no user, e.g. an agent): every upcoming interview. Interviewer: only their own."""
    if user and user.role == Role.interviewer:
        # ASSUMPTION: interviewers also see their past interviews, else they could not reach one to give feedback.
        rows = repository.list_upcoming(session, None, interviewer_email=user.email)
    else:
        rows = repository.list_upcoming(session, utcnow())
    return [{**i.model_dump(), "applicant_name": a.name, "job_title": j.title} for i, a, j in rows]

def schedule(session: Session, applicant_id: int, data: InterviewIn) -> dict:
    applicant = applicant_service.get(session, applicant_id)
    job = job_service.get(session, applicant.job_id)
    start, end = _free_slot(session, job, data)
    interview = repository.add(session, Interview(
        applicant_id=applicant_id, interviewer_name=data.interviewer_name.strip(),
        interviewer_email=data.interviewer_email, start=start, end=end, location=data.location.strip()))
    if applicant.stage in STAGES_BEFORE_INTERVIEW:
        applicant_service.change_stage(session, applicant, Stage.interview)
    applicant_repo.add_activity(session, applicant_id,
                                f"Interview scheduled {_when(start)} with {_who(interview)}")
    return _save_and_email(session, applicant, job, interview, "REQUEST")

def reschedule(session: Session, interview_id: int, data: InterviewIn) -> dict:
    interview = _get_scheduled(session, interview_id)
    applicant = applicant_service.get(session, interview.applicant_id)
    job = job_service.get(session, applicant.job_id)
    interview.start, interview.end = _free_slot(session, job, data, exclude_id=interview.id)
    interview.interviewer_name = data.interviewer_name.strip()
    interview.interviewer_email = data.interviewer_email
    interview.location = data.location.strip()
    interview.sequence += 1
    applicant_repo.add_activity(session, applicant.id,
                                f"Interview rescheduled to {_when(interview.start)} with {_who(interview)}")
    return _save_and_email(session, applicant, job, interview, "REQUEST")

def cancel(session: Session, interview_id: int) -> dict:
    interview = _get_scheduled(session, interview_id)
    applicant = applicant_service.get(session, interview.applicant_id)
    job = job_service.get(session, applicant.job_id)
    interview.status = InterviewStatus.cancelled
    interview.sequence += 1
    applicant_repo.add_activity(session, applicant.id, f"Interview {_when(interview.start)} cancelled")
    return _save_and_email(session, applicant, job, interview, "CANCEL")

def record_feedback(session: Session, interview_id: int, data: FeedbackIn, user: User | None = None) -> Interview:
    interview = _get(session, interview_id)
    if user and user.role == Role.interviewer and interview.interviewer_email.lower() != user.email.lower():
        raise Forbidden("You can only give feedback on your own interviews")
    if data.status not in (InterviewStatus.done, InterviewStatus.no_show):
        raise Invalid("Feedback status must be done or no_show")
    if interview.status == InterviewStatus.cancelled:
        raise Conflict("Interview was cancelled")
    if as_utc(interview.start) > utcnow():
        raise Invalid("Feedback can only be given after the interview has started")
    if data.status == InterviewStatus.done and data.score is None:
        raise Invalid("A score from 1 to 5 is required when the interview is done")
    interview.status = data.status
    interview.score = data.score
    interview.recommendation = data.recommendation
    interview.feedback = data.feedback.strip()
    verdict = f", score {data.score}/5" if data.score else ""
    verdict += f", {data.recommendation}" if data.recommendation else ""
    applicant_repo.add_activity(session, interview.applicant_id,
                                f"Interview {_when(interview.start)}: {data.status}{verdict}")
    session.commit()
    session.refresh(interview)
    return interview

def _get(session: Session, interview_id: int) -> Interview:
    interview = repository.get(session, interview_id)
    if not interview:
        raise NotFound("Interview not found")
    return interview

def _get_scheduled(session: Session, interview_id: int) -> Interview:
    interview = _get(session, interview_id)
    if interview.status != InterviewStatus.scheduled:
        raise Conflict(f"Only scheduled interviews can be changed (this one is {interview.status})")
    return interview

def _free_slot(session: Session, job: Job, data: InterviewIn, exclude_id: int | None = None) -> tuple[datetime, datetime]:
    start = as_utc(data.start)
    if start <= utcnow():
        raise Invalid("Interview time must be in the future")
    end = start + timedelta(minutes=job.interview_duration_minutes)
    if repository.find_clash(session, data.interviewer_email, start, end, exclude_id):
        raise Conflict("The interviewer already has an interview at that time")
    return start, end

def _when(dt: datetime) -> str:
    return as_utc(dt).astimezone(ZoneInfo(settings.timezone_name())).strftime("%a %d/%m/%Y %H:%M (%Z)")

def _who(interview: Interview) -> str:
    return interview.interviewer_name or interview.interviewer_email

def ics_uid(interview: Interview) -> str:
    # Stable per interview: Gmail/Outlook replace (or remove) the same event on every update.
    return f"interview-{interview.id}@hr-system"

def _save_and_email(session: Session, applicant: Applicant, job: Job, interview: Interview, method: str) -> dict:
    # Saved before emailing: a mail failure is reported, never loses the change.
    session.commit()
    session.refresh(interview)
    emailed, mail_error = _send_invitation(applicant, job, interview, method)
    label = "Cancellation" if method == "CANCEL" else "Invitation"
    applicant_repo.add_activity(session, applicant.id,
                                f"{label} emailed" if emailed else f"{label} not sent: {mail_error}")
    session.commit()
    session.refresh(interview)  # commit expires loaded objects; reload before serializing
    return {"interview": interview, "emailed": emailed, "mail_error": mail_error}

def _send_invitation(applicant: Applicant, job: Job, interview: Interview, method: str) -> tuple[bool, str | None]:
    if not mail_configured():
        return False, "Email is not configured (SMTP_HOST), email not sent"
    attendees = [applicant.email, interview.interviewer_email]
    summary = f"Interview: {applicant.name} - {job.title}"
    when = _when(interview.start)
    if method == "CANCEL":
        subject, text = f"Cancelled: {summary}", f"your interview for {job.title} on {when} has been cancelled."
    else:
        subject = f"Updated: {summary}" if interview.sequence else summary
        text = (f"your interview for {job.title} is scheduled for {when}, {job.interview_duration_minutes} minutes.\n"
                f"Location: {interview.location or 'to be confirmed'}\n\nThe attached invitation updates your calendar.")
    try:
        send_invite(
            to=attendees, subject=subject, body=f"Hello {applicant.name},\n\n{text}\n", method=method,
            ics=build_ics(ics_uid(interview), summary, interview.start, interview.end, interview.location,
                          mail_from(), attendees, method=method, sequence=interview.sequence),
        )
    except MailError as e:
        return False, str(e)
    return True, None
