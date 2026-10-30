"""Interview routes. Recruiters/admins: everything. Interviewers: list and give feedback on their own interviews only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter, require_user
from app.modules.interviews import service
from app.modules.interviews.models import CandidateResponse
from app.modules.interviews.schemas import FeedbackIn, InterviewIn
from app.modules.users.models import User

router = APIRouter(prefix="/api", tags=["interviews"])
# No login: the candidate opens these from the invitation email; the random token is the key.
public_router = APIRouter(prefix="/api/public/interviews", tags=["candidate"])

@router.get("/interviews")
def upcoming_interviews(user: User = Depends(require_user), session: Session = Depends(get_session)):
    return service.upcoming(session, user)

@router.post("/applicants/{applicant_id}/interviews", status_code=201, dependencies=[Depends(require_recruiter)])
def schedule_interview(applicant_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return service.schedule(session, applicant_id, data)

@router.put("/interviews/{interview_id}", dependencies=[Depends(require_recruiter)])
def reschedule_interview(interview_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return service.reschedule(session, interview_id, data)

@router.post("/interviews/{interview_id}/cancel", dependencies=[Depends(require_recruiter)])
def cancel_interview(interview_id: int, session: Session = Depends(get_session)):
    return service.cancel(session, interview_id)

@router.post("/interviews/{interview_id}/feedback")
def interview_feedback(interview_id: int, data: FeedbackIn, user: User = Depends(require_user),
                       session: Session = Depends(get_session)):
    return service.record_feedback(session, interview_id, data, user)

@router.get("/interviewers/{user_id}/free-slots", dependencies=[Depends(require_recruiter)])
def free_slots(user_id: int, applicant_id: int, days: int = Query(7, ge=1, le=31),
               session: Session = Depends(get_session)):
    return service.interviewer_free_slots(session, user_id, applicant_id, days)

@router.get("/interviewers/busy", dependencies=[Depends(require_recruiter)])
def team_calendar(user_ids: list[int] = Query(min_length=1, max_length=20), start: datetime = Query(),
                  days: int = Query(7, ge=1, le=31), session: Session = Depends(get_session)):
    """Busy blocks for the week grid (repeat ?user_ids=); start must carry a timezone."""
    return service.team_calendar(session, user_ids, start, days)

@public_router.get("/{token}")
def candidate_view(token: str, session: Session = Depends(get_session)):
    return service.candidate_view(session, token)

@public_router.post("/{token}/response")
def candidate_response(token: str, answer: CandidateResponse = Query(), session: Session = Depends(get_session)):
    return service.record_response(session, token, answer)
