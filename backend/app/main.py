"""HTTP API. /api/public/* is the careers site (no login); the rest is for recruiters.

Run: uvicorn app.main:app --reload  (from backend/)
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # before importing db, which reads DATABASE_URL

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel, EmailStr  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.cv import CvError, save_cv, upload_dir  # noqa: E402
from app.db import create_tables, get_session  # noqa: E402
from app.models import Activity, Applicant, Job, Stage  # noqa: E402

# ponytail: recruiter endpoints have no auth yet; add login before exposing beyond localhost.


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="HR System API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


class JobIn(BaseModel):
    title: str
    department: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    interview_duration_minutes: int = 45
    openings: int = 1
    is_open: bool = True


class StageIn(BaseModel):
    stage: Stage


class PublicJob(BaseModel):
    """What the careers site shows; internal fields like interview duration stay private."""
    id: int
    title: str
    department: str
    location: str
    description: str
    requirements: str


def _job_or_404(session: Session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


def _applicant_or_404(session: Session, applicant_id: int) -> Applicant:
    applicant = session.get(Applicant, applicant_id)
    if not applicant:
        raise HTTPException(404, "Applicant not found")
    return applicant


def _log(session: Session, applicant_id: int, message: str) -> None:
    session.add(Activity(applicant_id=applicant_id, message=message))


@app.get("/api/health")
def health():
    return {"ok": True}


# ------------------------------------------------------------------ careers site (public)

@app.get("/api/public/jobs", response_model=list[PublicJob])
def public_jobs(session: Session = Depends(get_session)):
    return session.exec(select(Job).where(Job.is_open).order_by(Job.created_at.desc())).all()


@app.get("/api/public/jobs/{job_id}", response_model=PublicJob)
def public_job(job_id: int, session: Session = Depends(get_session)):
    job = _job_or_404(session, job_id)
    if not job.is_open:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/public/jobs/{job_id}/apply", status_code=201)
async def apply(
    job_id: int,
    name: str = Form(min_length=1, max_length=200),
    email: EmailStr = Form(),
    phone: str = Form("", max_length=50),
    cv: UploadFile = File(),
    session: Session = Depends(get_session),
):
    job = _job_or_404(session, job_id)
    if not job.is_open:
        raise HTTPException(404, "Job not found")
    duplicate = session.exec(select(Applicant).where(Applicant.job_id == job_id, Applicant.email == email)).first()
    if duplicate:
        raise HTTPException(409, "You have already applied for this job")
    try:
        stored, text = save_cv(cv.filename or "", await cv.read())
    except CvError as e:
        raise HTTPException(422, str(e)) from e
    applicant = Applicant(job_id=job_id, name=name.strip(), email=email, phone=phone.strip(),
                          cv_filename=cv.filename or stored, cv_path=stored, cv_text=text)
    session.add(applicant)
    session.flush()
    _log(session, applicant.id, "Applied through the careers site")
    session.commit()
    return {"id": applicant.id}


# ------------------------------------------------------------------ recruiter

@app.get("/api/jobs")
def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    counts: dict[int, int] = {}
    for job_id in session.exec(select(Applicant.job_id)).all():
        counts[job_id] = counts.get(job_id, 0) + 1
    return [{**job.model_dump(), "applicant_count": counts.get(job.id, 0)} for job in jobs]


@app.post("/api/jobs", status_code=201)
def create_job(data: JobIn, session: Session = Depends(get_session)):
    job = Job.model_validate(data)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@app.put("/api/jobs/{job_id}")
def update_job(job_id: int, data: JobIn, session: Session = Depends(get_session)):
    job = _job_or_404(session, job_id)
    job.sqlmodel_update(data.model_dump())
    session.commit()
    session.refresh(job)
    return job


@app.get("/api/stages")
def list_stages():
    return [s.value for s in Stage]


@app.get("/api/applicants")
def list_applicants(job_id: int | None = None, session: Session = Depends(get_session)):
    query = select(Applicant).order_by(Applicant.created_at.desc())
    if job_id is not None:
        query = query.where(Applicant.job_id == job_id)
    # cv_text can be long; the board only needs the card fields.
    return [a.model_dump(exclude={"cv_text", "cv_path"}) for a in session.exec(query).all()]


@app.get("/api/applicants/{applicant_id}")
def get_applicant(applicant_id: int, session: Session = Depends(get_session)):
    applicant = _applicant_or_404(session, applicant_id)
    activity = session.exec(
        select(Activity).where(Activity.applicant_id == applicant_id).order_by(Activity.created_at)).all()
    return {**applicant.model_dump(exclude={"cv_path"}), "activity": activity}


@app.patch("/api/applicants/{applicant_id}/stage")
def move_stage(applicant_id: int, data: StageIn, session: Session = Depends(get_session)):
    applicant = _applicant_or_404(session, applicant_id)
    if applicant.stage != data.stage:
        _log(session, applicant_id, f"Stage: {applicant.stage} → {data.stage}")
        applicant.stage = data.stage
        session.commit()
    return {"id": applicant_id, "stage": applicant.stage}


@app.get("/api/applicants/{applicant_id}/cv")
def download_cv(applicant_id: int, session: Session = Depends(get_session)):
    applicant = _applicant_or_404(session, applicant_id)
    if not applicant.cv_path:
        raise HTTPException(404, "No CV uploaded")
    return FileResponse(upload_dir() / applicant.cv_path, filename=applicant.cv_filename)
