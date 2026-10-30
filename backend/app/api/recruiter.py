"""Recruiter routes (login required): jobs, applicant board, stage moves, CV download, interviews."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import require_recruiter
from app.models import Stage
from app.schemas import InterviewIn, JobIn, StageIn
from app.services import applicants, interviews, jobs

router = APIRouter(prefix="/api", tags=["recruiter"], dependencies=[Depends(require_recruiter)])


@router.get("/jobs")
def list_jobs(session: Session = Depends(get_session)):
    return jobs.list_with_counts(session)


@router.post("/jobs", status_code=201)
def create_job(data: JobIn, session: Session = Depends(get_session)):
    return jobs.create(session, data)


@router.put("/jobs/{job_id}")
def update_job(job_id: int, data: JobIn, session: Session = Depends(get_session)):
    return jobs.update(session, job_id, data)


@router.get("/stages")
def list_stages():
    return [s.value for s in Stage]


@router.get("/applicants")
def list_applicants(job_id: int | None = None, session: Session = Depends(get_session)):
    return applicants.list_for_board(session, job_id)


@router.get("/applicants/{applicant_id}")
def get_applicant(applicant_id: int, session: Session = Depends(get_session)):
    return applicants.detail(session, applicant_id)


@router.patch("/applicants/{applicant_id}/stage")
def move_stage(applicant_id: int, data: StageIn, session: Session = Depends(get_session)):
    applicant = applicants.move_stage(session, applicant_id, data.stage)
    return {"id": applicant.id, "stage": applicant.stage}


@router.get("/applicants/{applicant_id}/cv")
def download_cv(applicant_id: int, session: Session = Depends(get_session)):
    path, filename = applicants.cv_file(session, applicant_id)
    return FileResponse(path, filename=filename)


@router.get("/interviews")
def upcoming_interviews(session: Session = Depends(get_session)):
    return interviews.upcoming(session)


@router.post("/applicants/{applicant_id}/interviews", status_code=201)
def schedule_interview(applicant_id: int, data: InterviewIn, session: Session = Depends(get_session)):
    return interviews.schedule(session, applicant_id, data)
