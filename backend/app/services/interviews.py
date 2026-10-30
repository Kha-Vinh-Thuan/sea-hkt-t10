"""Interviews: book a slot (job length, no past times, no interviewer double booking), email the .ics invite."""

import os
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.integrations.mail import MailError, build_ics, mail_configured, mail_from, send_invite
from app.models import Applicant, Interview, Job, Stage, utcnow
from app.schemas import InterviewIn
from app.services.applicants import log
from app.services.errors import Conflict, Invalid, fetch

# Booking an interview moves early-stage applicants forward; later stages (offer, hired...) stay put.
STAGES_BEFORE_INTERVIEW = {Stage.new, Stage.screening}


def upcoming(session: Session) -> list[dict]:
    rows = session.exec(
        select(Interview, Applicant, Job)
        .join(Applicant, Interview.applicant_id == Applicant.id)
        .join(Job, Applicant.job_id == Job.id)
        .where(Interview.end >= utcnow())
        .order_by(Interview.start)
    ).all()
    return [{**i.model_dump(), "applicant_name": a.name, "job_title": j.title} for i, a, j in rows]


def schedule(session: Session, applicant_id: int, data: InterviewIn) -> dict:
    applicant = fetch(session, Applicant, applicant_id)
    job = fetch(session, Job, applicant.job_id)
    start = data.start.astimezone(timezone.utc)
    if start <= utcnow():
        raise Invalid("Interview time must be in the future")
    end = start + timedelta(minutes=job.interview_duration_minutes)
    clash = session.exec(select(Interview).where(
        Interview.interviewer_email == data.interviewer_email, Interview.start < end, Interview.end > start)).first()
    if clash:
        raise Conflict("The interviewer already has an interview at that time")

    interview = Interview(applicant_id=applicant_id, interviewer_name=data.interviewer_name.strip(),
                          interviewer_email=data.interviewer_email, start=start, end=end,
                          location=data.location.strip())
    session.add(interview)
    if applicant.stage in STAGES_BEFORE_INTERVIEW:
        log(session, applicant_id, f"Stage: {applicant.stage} → {Stage.interview}")
        applicant.stage = Stage.interview
    when = start.astimezone(ZoneInfo(os.environ.get("TIMEZONE", "Asia/Ho_Chi_Minh"))).strftime("%a %d/%m/%Y %H:%M (%Z)")
    log(session, applicant_id, f"Interview scheduled {when} with {data.interviewer_name or data.interviewer_email}")
    session.commit()
    session.refresh(interview)

    # Saved before emailing: a mail failure is reported, never loses the booking.
    emailed, mail_error = _send_invitation(applicant, job, interview, when)
    log(session, applicant_id, "Invitation emailed" if emailed else f"Invitation not sent: {mail_error}")
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
