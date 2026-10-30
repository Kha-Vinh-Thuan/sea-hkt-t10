"""Report routes: recruitment summary per job."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.reports import service

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_recruiter)])

@router.get("/summary")
def summary(job_id: int | None = None, session: Session = Depends(get_session)):
    return service.summary(session, job_id)
