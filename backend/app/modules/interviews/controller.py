"""Interview routes (recruiter): upcoming list, booking, reschedule, cancel, feedback."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.interviews import service
from app.modules.interviews.schemas import FeedbackIn, InterviewIn

router = APIRouter(prefix="/api", tags=["interviews"], dependencies=[Depends(require_recruiter)])

@router.get("/interviews")
def upcoming_interviews(session: Session = Depends(get_session)):
    return service.upcoming(session)

@router.post("/applicants/{applicant_id}/interviews", status_code=201)
def schedule_interview(applicant_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return service.schedule(session, applicant_id, data)

@router.put("/interviews/{interview_id}")
def reschedule_interview(interview_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return service.reschedule(session, interview_id, data)

@router.post("/interviews/{interview_id}/cancel")
def cancel_interview(interview_id: int, session: Session = Depends(get_session)):
    return service.cancel(session, interview_id)

@router.post("/interviews/{interview_id}/feedback")
def interview_feedback(interview_id: int, data: FeedbackIn, session: Session = Depends(get_session)):
    return service.record_feedback(session, interview_id, data)
