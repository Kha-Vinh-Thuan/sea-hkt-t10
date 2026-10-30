"""Applicant routes: public apply form and the recruiter board (edit, refuse, archive / restore)."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import EmailStr
from sqlmodel import Session

from app.config.database import get_session
from app.modules.applicants import service
from app.modules.applicants.models import STUCK_AFTER_DAYS, RefuseReason, Source, Stage
from app.modules.applicants.schemas import ApplicantUpdate, RefuseIn, StageIn
from app.modules.auth.dependencies import require_recruiter

public_router = APIRouter(prefix="/api/public/jobs", tags=["careers"])
router = APIRouter(prefix="/api", tags=["applicants"], dependencies=[Depends(require_recruiter)])

# The board / drawer never needs the stored file name or the (long) CV text in these responses.
CARD_EXCLUDE = {"cv_text", "cv_path"}

# Labels live here so the UI shows readable reasons without keeping its own copy of the list.
REFUSE_REASON_LABELS = {
    RefuseReason.does_not_fit: "Does not fit the job requirements",
    RefuseReason.refused_job_fit: "Refused by applicant: job fit",
    RefuseReason.refused_salary: "Refused by applicant: salary",
    RefuseReason.job_filled: "Job already filled",
    RefuseReason.duplicate: "Duplicate",
    RefuseReason.spam: "Spam",
}


@public_router.post("/{job_id}/apply", status_code=201)
async def apply(
    job_id: int,
    name: str = Form(min_length=1, max_length=200),
    email: EmailStr = Form(),
    phone: str = Form("", max_length=50),
    linkedin: str = Form("", max_length=500),
    short_intro: str = Form("", max_length=service.MAX_INTRO),
    source: Source = Form(Source.careers_site),  # from the careers URL, e.g. /careers/1?source=linkedin
    cv: UploadFile = File(),
    session: Session = Depends(get_session),
):
    applicant = service.apply(session, job_id, name, email, phone, cv.filename or "", await cv.read(),
                              linkedin=linkedin, short_intro=short_intro, source=source)
    return {"id": applicant.id}


@router.get("/stages")
def list_stages():
    return [s.value for s in Stage]


@router.get("/stage-rules")
def stage_rules():
    # Separate from /stages so that endpoint stays a plain list for existing callers. None = never stuck.
    return {"stuck_after_days": {stage.value: days for stage, days in STUCK_AFTER_DAYS.items()}}


@router.get("/refuse-reasons")
def list_refuse_reasons():
    return [{"value": r.value, "label": REFUSE_REASON_LABELS.get(r, r.value)} for r in RefuseReason]


@router.get("/applicants")
def list_applicants(job_id: int | None = None, archived: bool = False, q: str = Query("", max_length=200),
                    priority_min: int | None = Query(None, ge=0, le=3), tag: str = Query("", max_length=100),
                    session: Session = Depends(get_session)):
    return service.list_for_board(session, job_id, archived, q, priority_min, tag)


@router.get("/applicants/{applicant_id}")
def get_applicant(applicant_id: int, session: Session = Depends(get_session)):
    return service.detail(session, applicant_id)


@router.patch("/applicants/{applicant_id}")
def update_applicant(applicant_id: int, data: ApplicantUpdate, session: Session = Depends(get_session)):
    return service.update(session, applicant_id, data).model_dump(exclude=CARD_EXCLUDE)


@router.patch("/applicants/{applicant_id}/stage")
def move_stage(applicant_id: int, data: StageIn, session: Session = Depends(get_session)):
    applicant = service.move_stage(session, applicant_id, data.stage)
    return {"id": applicant.id, "stage": applicant.stage}


@router.post("/applicants/{applicant_id}/refuse")
def refuse(applicant_id: int, data: RefuseIn, session: Session = Depends(get_session)):
    return service.refuse(session, applicant_id, data.reason, data.send_email)


@router.post("/applicants/{applicant_id}/archive")
def archive(applicant_id: int, session: Session = Depends(get_session)):
    return service.archive(session, applicant_id).model_dump(exclude=CARD_EXCLUDE)


@router.post("/applicants/{applicant_id}/restore")
def restore(applicant_id: int, session: Session = Depends(get_session)):
    return service.restore(session, applicant_id).model_dump(exclude=CARD_EXCLUDE)


@router.get("/applicants/{applicant_id}/cv")
def download_cv(applicant_id: int, session: Session = Depends(get_session)):
    path, filename = service.cv_file(session, applicant_id)
    return FileResponse(path, filename=filename)
