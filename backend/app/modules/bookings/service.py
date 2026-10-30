"""Propose interview times by email and let the candidate book one (Odoo-like self-scheduling).

Recruiter picks slots -> candidate gets {FRONTEND_URL}/book/{token} -> public page lists the slots still free ->
booking goes through the normal interviews.schedule (same checks, invite mail, Google event).
"""

from datetime import datetime, timedelta

from sqlmodel import Session

from app.config import settings
from app.integrations.mail import MailError, mail_configured, send_mail
from app.modules.applicants import repository as applicant_repo
from app.modules.applicants import service as applicant_service
from app.modules.bookings import repository
from app.modules.bookings.models import ProposalStatus, SlotProposal
from app.modules.bookings.schemas import ProposalIn
from app.modules.interviews import availability
from app.modules.interviews import service as interview_service
from app.modules.interviews.schemas import InterviewIn
from app.modules.jobs import service as job_service
from app.modules.users import service as user_service
from app.utils.errors import Conflict, Gone, Invalid, NotFound
from app.utils.time import as_utc, utcnow

PROPOSAL_SUBJECT = "Pick a time for your interview: {job}"
PROPOSAL_BODY = (
    "Hello {name},\n\nWe would like to invite you to an interview for {job} ({minutes} minutes).\n"
    "Please pick the time that suits you best here:\n{link}\n\nThe link is valid until {expires}.\n"
)

def propose(session: Session, applicant_id: int, data: ProposalIn) -> dict:
    applicant = applicant_service.get(session, applicant_id)
    job = job_service.get(session, applicant.job_id)
    interviewer = user_service.get_active(session, data.interviewer_id)
    if not interviewer:
        raise Invalid("Unknown or inactive interviewer")
    starts = sorted({as_utc(s) for s in data.slots})
    if starts[0] <= utcnow():
        raise Invalid("Proposed times must be in the future")
    proposal = SlotProposal(applicant_id=applicant_id, interviewer_id=interviewer.id,
                            slots=[s.isoformat() for s in starts], location=data.location.strip())
    session.add(proposal)
    applicant_repo.add_activity(session, applicant_id,
                                f"{len(starts)} interview times proposed with {interviewer.name or interviewer.email}")
    session.commit()
    session.refresh(proposal)

    link = f"{settings.frontend_url()}/book/{proposal.token}"
    values = {"name": applicant.name, "job": job.title, "minutes": job.interview_duration_minutes, "link": link,
              "expires": interview_service.when(proposal.expires_at)}
    error = None
    if not mail_configured():
        error = "Email is not configured (SMTP_HOST)"
    else:
        try:
            send_mail([applicant.email], PROPOSAL_SUBJECT.format(**values), PROPOSAL_BODY.format(**values))
        except MailError as e:
            error = str(e)
    applicant_repo.add_activity(session, applicant_id,
                                "Time proposal emailed" if error is None else f"Time proposal not sent: {error}")
    session.commit()
    return {"id": proposal.id, "link": link, "emailed": error is None, "mail_error": error}

def public_view(session: Session, token: str) -> dict:
    """The booking page: job, candidate first name, and the proposed times that are still free."""
    proposal = _open_proposal(session, token)
    applicant = applicant_service.get(session, proposal.applicant_id)
    job = job_service.get(session, applicant.job_id)
    free = _free(session, proposal, job.interview_duration_minutes)
    return {"job_title": job.title, "candidate_name": applicant.name, "minutes": job.interview_duration_minutes,
            "location": proposal.location, "expires_at": proposal.expires_at,
            "slots": [{"start": s, "end": e} for s, e in free]}

def book(session: Session, token: str, start: datetime) -> dict:
    proposal = _open_proposal(session, token)
    applicant = applicant_service.get(session, proposal.applicant_id)
    job = job_service.get(session, applicant.job_id)
    start = as_utc(start)
    if start not in [s for s, _ in _free(session, proposal, job.interview_duration_minutes)]:
        raise Conflict("That time is no longer available, please pick another one")
    interviewer = user_service.get(session, proposal.interviewer_id)
    # The interviews service re-checks the clash and sends the usual invitation (.ics, Accept / Decline links).
    result = interview_service.schedule(session, applicant.id, InterviewIn(
        start=start, interviewer_name=interviewer.name, interviewer_email=interviewer.email,
        location=proposal.location))
    proposal.status = ProposalStatus.booked
    session.add(proposal)
    applicant_repo.add_activity(session, applicant.id,
                                f"Candidate booked {interview_service.when(start)} from the proposed times")
    session.commit()
    interview = result["interview"]
    return {"start": interview.start, "end": interview.end, "location": interview.location,
            "meet_url": interview.meet_url, "emailed": result["emailed"]}

def _open_proposal(session: Session, token: str) -> SlotProposal:
    proposal = repository.get_by_token(session, token)
    if not proposal:
        raise NotFound("Unknown booking link")
    if proposal.status == ProposalStatus.booked:
        raise Conflict("This interview has already been booked")
    if proposal.status == ProposalStatus.expired or as_utc(proposal.expires_at) <= utcnow():
        if proposal.status != ProposalStatus.expired:
            proposal.status = ProposalStatus.expired
            session.add(proposal)
            session.commit()
        raise Gone("This booking link has expired, please ask the recruiter for new times")
    return proposal

def _free(session: Session, proposal: SlotProposal, minutes: int) -> list[tuple[datetime, datetime]]:
    length = timedelta(minutes=minutes)
    slots = [(as_utc(datetime.fromisoformat(s)), as_utc(datetime.fromisoformat(s)) + length) for s in proposal.slots]
    return availability.still_free(session, proposal.interviewer_id, slots)
