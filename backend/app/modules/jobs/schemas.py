"""Job request/response shapes."""

from datetime import date

from pydantic import BaseModel, Field

from app.modules.jobs.models import EmploymentType


class PublicJob(BaseModel):
    """What the careers site shows; internal fields like interview duration stay private."""
    id: int
    title: str
    department: str
    location: str
    description: str
    requirements: str
    employment_type: EmploymentType
    is_remote: bool
    salary_min: int | None
    salary_max: int | None
    expected_degree: str
    tags: list[str]
    opens_on: date | None
    closes_on: date | None


class JobIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    interview_duration_minutes: int = Field(45, gt=0, le=480)
    openings: int = Field(1, ge=0)
    is_open: bool = True
    opens_on: date | None = None
    closes_on: date | None = None
    employment_type: EmploymentType = EmploymentType.full_time
    is_remote: bool = False
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    expected_degree: str = Field("", max_length=200)
    recruiter_id: int | None = None
    manager_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=30)
    # None on update = keep the current list.
    interviewer_ids: list[int] | None = Field(None, max_length=50)
