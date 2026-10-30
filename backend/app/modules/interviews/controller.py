"""Interview routes. Recruiters/admins: everything. Interviewers: list and give feedback on their own interviews only."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter, require_user
from app.modules.interviews import service
from app.modules.interviews.schemas import FeedbackIn, InterviewIn
from app.modules.users.models import User

router = APIRouter(prefix="/api", tags=["interviews"])

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
