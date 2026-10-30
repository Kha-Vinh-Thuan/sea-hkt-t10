"""Careers site routes (no login): open jobs and the apply form."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import EmailStr
from sqlmodel import Session

from app.core.db import get_session
from app.schemas import PublicJob
from app.services import applicants, jobs

router = APIRouter(prefix="/api/public", tags=["careers"])


@router.get("/jobs", response_model=list[PublicJob])
def list_open_jobs(session: Session = Depends(get_session)):
    return jobs.list_open(session)


@router.get("/jobs/{job_id}", response_model=PublicJob)
def get_open_job(job_id: int, session: Session = Depends(get_session)):
    return jobs.open_job(session, job_id)


@router.post("/jobs/{job_id}/apply", status_code=201)
async def apply(
    job_id: int,
    name: str = Form(min_length=1, max_length=200),
    email: EmailStr = Form(),
    phone: str = Form("", max_length=50),
    cv: UploadFile = File(),
    session: Session = Depends(get_session),
):
    applicant = applicants.apply(session, job_id, name, email, phone, cv.filename or "", await cv.read())
    return {"id": applicant.id}
