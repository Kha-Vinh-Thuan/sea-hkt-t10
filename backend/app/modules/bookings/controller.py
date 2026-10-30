"""Slot proposal routes: the recruiter proposes times; the candidate (no login, token in the link) books one."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.bookings import service
from app.modules.bookings.schemas import BookIn, ProposalIn

router = APIRouter(prefix="/api", tags=["bookings"], dependencies=[Depends(require_recruiter)])
public_router = APIRouter(prefix="/api/public/bookings", tags=["candidate"])

@router.post("/applicants/{applicant_id}/slot-proposals", status_code=201)
def propose(applicant_id: int, data: ProposalIn, session: Session = Depends(get_session)):
    return service.propose(session, applicant_id, data)

@public_router.get("/{token}")
def booking_page(token: str, session: Session = Depends(get_session)):
    return service.public_view(session, token)

@public_router.post("/{token}")
def book(token: str, data: BookIn, session: Session = Depends(get_session)):
    return service.book(session, token, data.start)
