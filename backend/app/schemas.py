"""Request/response shapes of the HTTP API. Tables live in models.py; these are what clients send and see."""

from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from app.models import Stage


class PublicJob(BaseModel):
    """What the careers site shows; internal fields like interview duration stay private."""
    id: int
    title: str
    department: str
    location: str
    description: str
    requirements: str


class JobIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    interview_duration_minutes: int = Field(45, gt=0, le=480)
    openings: int = Field(1, ge=0)
    is_open: bool = True


class StageIn(BaseModel):
    stage: Stage


class InterviewIn(BaseModel):
    start: AwareDatetime
    interviewer_name: str = Field("", max_length=200)
    interviewer_email: EmailStr
    location: str = Field("", max_length=500)


class LoginIn(BaseModel):
    email: str
    password: str
