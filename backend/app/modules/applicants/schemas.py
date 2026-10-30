"""Applicant request shapes."""

from datetime import date

from pydantic import BaseModel, Field

from app.modules.applicants.models import RefuseReason, Stage

class StageIn(BaseModel):
    stage: Stage

class ApplicantUpdate(BaseModel):
    # Partial update: the service only applies fields present in the request (exclude_unset).
    notes: str = Field("", max_length=10_000)
    priority: int = Field(0, ge=0, le=3)
    tags: list[str] = Field(default_factory=list, max_length=30)
    linkedin: str = Field("", max_length=500)
    available_from: date | None = None
    degree: str = Field("", max_length=200)
    salary_expected: int | None = Field(None, ge=0)
    salary_proposed: int | None = Field(None, ge=0)

class RefuseIn(BaseModel):
    reason: RefuseReason
    send_email: bool = False
