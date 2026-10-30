"""Interview routes (recruiter): upcoming list and booking."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.interviews import service
from app.modules.interviews.schemas import InterviewIn

router = APIRouter(prefix="/api", tags=["interviews"], dependencies=[Depends(require_recruiter)])


@router.get("/interviews")
def upcoming_interviews(session: Session = Depends(get_session)):
    return service.upcoming(session)


@router.post("/applicants/{applicant_id}/interviews", status_code=201)
def schedule_interview(applicant_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return service.schedule(session, applicant_id, data)
