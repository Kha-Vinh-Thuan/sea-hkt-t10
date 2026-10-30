"""Mirror an interview onto the interviewer's Google Calendar (create / move / delete, Meet link).

Only when the interviewer is a user who connected Google. Called after the booking is committed, so a Google
failure never undoes it: the caller logs the returned error in the applicant activity.
"""

from sqlmodel import Session

from app.integrations import google_calendar
from app.integrations.google_calendar import GoogleError
from app.modules.applicants.models import Applicant
from app.modules.google import service as google_service
from app.modules.interviews.models import Interview, InterviewStatus
from app.modules.jobs.models import Job

def sync(session: Session, interview: Interview, applicant: Applicant, job: Job,
         old_interviewer_email: str | None = None) -> str | None:
    """Bring the Google event in line with the interview. Returns an error message, or None (synced or nothing to do).

    `old_interviewer_email`: on reschedule to another interviewer the event lives on the old one's calendar.
    """
    try:
        if old_interviewer_email and old_interviewer_email.lower() != interview.interviewer_email.lower():
            _delete(session, interview, old_interviewer_email)
        if interview.status == InterviewStatus.cancelled:
            _delete(session, interview, interview.interviewer_email)
        else:
            _save(session, interview, applicant, job)
    except GoogleError as e:
        return str(e)
    return None

def _delete(session: Session, interview: Interview, interviewer_email: str) -> None:
    refresh_token = google_service.refresh_token_for_email(session, interviewer_email)
    if interview.google_event_id and refresh_token:
        google_calendar.delete_event(refresh_token, interview.google_event_id)
    interview.google_event_id = interview.meet_url = ""

def _save(session: Session, interview: Interview, applicant: Applicant, job: Job) -> None:
    refresh_token = google_service.refresh_token_for_email(session, interview.interviewer_email)
    if not refresh_token:
        return
    body = google_calendar.event_body(
        f"Interview: {applicant.name} - {job.title}", f"Interview for {job.title}.", interview.start, interview.end,
        interview.location, [applicant.email], request_id=f"interview-{interview.id}-{interview.sequence}")
    if interview.google_event_id:
        body.pop("conferenceData")  # keep the existing Meet link when the event moves
    interview.google_event_id, meet_url = google_calendar.save_event(refresh_token, interview.google_event_id, body)
    interview.meet_url = meet_url or interview.meet_url
    if not interview.location and interview.meet_url:
        interview.location = interview.meet_url
