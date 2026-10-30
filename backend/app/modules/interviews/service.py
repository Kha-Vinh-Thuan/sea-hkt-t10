"""Interview rules: book / reschedule / cancel (job length, no past times, no interviewer double booking,
email the .ics with a stable UID, mirror on the interviewer's Google Calendar), the candidate's Accept / Decline,
and the post-interview scorecard."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.integrations.mail import MailError, build_ics, mail_configured, mail_from, send_invite
from app.modules.applicants import repository as applicant_repo
from app.modules.applicants import service as applicant_service
from app.modules.applicants.models import Applicant, Stage
from app.modules.interviews import availability, calendar_sync, repository
from app.modules.interviews.models import CandidateResponse, Interview, InterviewStatus
from app.modules.interviews.schemas import FeedbackIn, InterviewIn
from app.modules.jobs import service as job_service
from app.modules.jobs.models import Job
from app.modules.users.models import Role, User
from app.utils.errors import Conflict, Forbidden, Gone, Invalid, NotFound
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
    return [{**i.model_dump(exclude={"response_token"}), "applicant_name": a.name, "job_title": j.title} for i, a, j in rows]

def interviewer_free_slots(session: Session, user_id: int, applicant_id: int, days: int) -> list[dict]:
    """Free slots of one interviewer over the next `days`, as long as this applicant's job interview."""
    job = job_service.get(session, applicant_service.get(session, applicant_id).job_id)
    now = utcnow()
    slots = availability.free_slots(session, user_id, now, now + timedelta(days=days), job.interview_duration_minutes)
    return [{"start": start, "end": end} for start, end in slots]

def team_calendar(session: Session, user_ids: list[int], start: datetime, days: int) -> list[dict]:
    """Busy blocks of several interviewers over `days` from `start`, for the week grid."""
    start = as_utc(start)
    return availability.week_busy(session, user_ids, start, start + timedelta(days=days))

def schedule(session: Session, applicant_id: int, data: InterviewIn) -> dict:
    applicant = applicant_service.get(session, applicant_id)
    job = job_service.get(session, applicant.job_id)
    start, end = _free_slot(session, job, applicant_id, data)
    interview = repository.add(session, Interview(
        applicant_id=applicant_id, interviewer_name=data.interviewer_name.strip(),
        interviewer_email=data.interviewer_email, start=start, end=end, location=data.location.strip()))
    if applicant.stage in STAGES_BEFORE_INTERVIEW:
        applicant_service.change_stage(session, applicant, Stage.interview)
    applicant_repo.add_activity(session, applicant_id,
                                f"Interview scheduled {when(start)} with {_who(interview)}")
    return _save_and_email(session, applicant, job, interview, "REQUEST")

def reschedule(session: Session, interview_id: int, data: InterviewIn) -> dict:
    interview = _get_scheduled(session, interview_id)
    applicant = applicant_service.get(session, interview.applicant_id)
    job = job_service.get(session, applicant.job_id)
    old_interviewer_email = interview.interviewer_email
    interview.start, interview.end = _free_slot(session, job, applicant.id, data, exclude_id=interview.id)
    interview.interviewer_name = data.interviewer_name.strip()
    interview.interviewer_email = data.interviewer_email
    interview.location = data.location.strip()
    interview.sequence += 1
    interview.candidate_response = CandidateResponse.none  # new time: ask the candidate again
    applicant_repo.add_activity(session, applicant.id,
                                f"Interview rescheduled to {when(interview.start)} with {_who(interview)}")
    return _save_and_email(session, applicant, job, interview, "REQUEST", old_interviewer_email)

def cancel(session: Session, interview_id: int) -> dict:
    interview = _get_scheduled(session, interview_id)
    applicant = applicant_service.get(session, interview.applicant_id)
    job = job_service.get(session, applicant.job_id)
    interview.status = InterviewStatus.cancelled
    interview.sequence += 1
    applicant_repo.add_activity(session, applicant.id, f"Interview {when(interview.start)} cancelled")
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
                                f"Interview {when(interview.start)}: {data.status}{verdict}")
    session.commit()
    session.refresh(interview)
    return interview

def candidate_view(session: Session, token: str) -> dict:
    """What the public Accept / Decline page shows. No interviewer email or internal fields."""
    interview = _by_token(session, token)
    applicant = applicant_service.get(session, interview.applicant_id)
    job = job_service.get(session, applicant.job_id)
    return {"job_title": job.title, "candidate_name": applicant.name, "start": interview.start, "end": interview.end,
            "location": interview.location, "meet_url": interview.meet_url, "status": interview.status,
            "candidate_response": interview.candidate_response}

def record_response(session: Session, token: str, answer: CandidateResponse) -> dict:
    interview = _by_token(session, token)
    if answer == CandidateResponse.none:
        raise Invalid("Answer must be accepted or declined")
    if interview.status != InterviewStatus.scheduled:
        raise Conflict(f"This interview is {interview.status}, it can no longer be answered")
    if as_utc(interview.end) <= utcnow():
        raise Gone("This interview is over")
    if interview.candidate_response != answer:
        interview.candidate_response = answer
        applicant_repo.add_activity(session, interview.applicant_id,
                                    f"Candidate {answer} the interview {when(interview.start)}")
        session.commit()
    return candidate_view(session, token)

def _by_token(session: Session, token: str) -> Interview:
    interview = repository.get_by_response_token(session, token)
    if not interview:
        raise NotFound("Unknown interview link")
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

def _free_slot(session: Session, job: Job, applicant_id: int, data: InterviewIn,
               exclude_id: int | None = None) -> tuple[datetime, datetime]:
    start = as_utc(data.start)
    if start <= utcnow():
        raise Invalid("Interview time must be in the future")
    end = start + timedelta(minutes=job.interview_duration_minutes)
    if repository.find_clash(session, data.interviewer_email, start, end, exclude_id):
        raise Conflict("The interviewer already has an interview at that time")
    # The calendar the recruiter (or an agent) looked at may be stale: re-ask Google right before saving.
    google = availability.check_google_free(session, data.interviewer_email, start, end)
    if google == "busy":
        raise Conflict("The interviewer is busy in Google Calendar at that time")
    if google:
        applicant_repo.add_activity(session, applicant_id, google)
    return start, end

def when(dt: datetime) -> str:
    return as_utc(dt).astimezone(ZoneInfo(settings.timezone_name())).strftime("%a %d/%m/%Y %H:%M (%Z)")

def _who(interview: Interview) -> str:
    return interview.interviewer_name or interview.interviewer_email

def ics_uid(interview: Interview) -> str:
    # Stable per interview: Gmail/Outlook replace (or remove) the same event on every update.
    return f"interview-{interview.id}@hr-system"

def _save_and_email(session: Session, applicant: Applicant, job: Job, interview: Interview, method: str,
                    old_interviewer_email: str | None = None) -> dict:
    # Saved before Google and email: their failures are reported, never lose the change.
    session.commit()
    session.refresh(interview)
    google_error = calendar_sync.sync(session, interview, applicant, job, old_interviewer_email)
    if google_error:
        applicant_repo.add_activity(session, applicant.id, f"Google Calendar not updated: {google_error}")
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
    at = when(interview.start)
    if method == "CANCEL":
        subject, text = f"Cancelled: {summary}", f"your interview for {job.title} on {at} has been cancelled."
    else:
        subject = f"Updated: {summary}" if interview.sequence else summary
        answer = f"{settings.frontend_url()}/interview/{interview.response_token}?answer="
        meet = (f"Google Meet: {interview.meet_url}\n"
                if interview.meet_url and interview.meet_url != interview.location else "")
        # ponytail: one mail to candidate + interviewer, so the interviewer sees the candidate's answer links too;
        # split into two mails if that matters.
        text = (f"your interview for {job.title} is scheduled for {at}, {job.interview_duration_minutes} minutes.\n"
                f"Location: {interview.location or 'to be confirmed'}\n{meet}\n"
                f"Please let us know if you can make it:\n  Accept: {answer}accept\n  Decline: {answer}decline\n\n"
                "The attached invitation updates your calendar.")
    try:
        send_invite(
            to=attendees, subject=subject, body=f"Hello {applicant.name},\n\n{text}\n", method=method,
            ics=build_ics(ics_uid(interview), summary, interview.start, interview.end, interview.location,
                          mail_from(), attendees, method=method, sequence=interview.sequence),
        )
    except MailError as e:
        return False, str(e)
    return True, None
