"""Applicant request shapes."""

from pydantic import BaseModel

from app.modules.applicants.models import Stage


class StageIn(BaseModel):
    stage: Stage
