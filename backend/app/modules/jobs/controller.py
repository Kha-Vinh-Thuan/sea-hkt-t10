"""Job routes: public careers listing and recruiter job management."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.jobs import service
from app.modules.jobs.schemas import JobIn, PublicJob

public_router = APIRouter(prefix="/api/public/jobs", tags=["careers"])
router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(require_recruiter)])


@public_router.get("", response_model=list[PublicJob])
def list_open_jobs(session: Session = Depends(get_session)):
    return service.list_open(session)


@public_router.get("/{job_id}", response_model=PublicJob)
def get_open_job(job_id: int, session: Session = Depends(get_session)):
    return service.get_open(session, job_id)


@router.get("")
def list_jobs(session: Session = Depends(get_session)):
    return service.list_with_counts(session)


@router.post("", status_code=201)
def create_job(data: JobIn, session: Session = Depends(get_session)):
    return service.create(session, data)


@router.put("/{job_id}")
def update_job(job_id: int, data: JobIn, session: Session = Depends(get_session)):
    return service.update(session, job_id, data)
