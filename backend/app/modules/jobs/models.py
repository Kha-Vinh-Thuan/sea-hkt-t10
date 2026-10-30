"""Job table, plus the fixed employment types."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow


class EmploymentType(StrEnum):
    full_time = "full_time"
    part_time = "part_time"
    internship = "internship"
    contract = "contract"


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    department: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    interview_duration_minutes: int = Field(default=45, gt=0)
    openings: int = Field(default=1, ge=0)
    is_open: bool = True
    opens_on: date | None = None    # None = open from day one
    closes_on: date | None = None   # inclusive; None = no deadline
    employment_type: EmploymentType = EmploymentType.full_time
    is_remote: bool = False
    # ASSUMPTION: salary is gross per month in VND until the product spec says otherwise.
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    expected_degree: str = ""
    recruiter_id: int | None = Field(default=None, foreign_key="app_user.id")
    manager_id: int | None = Field(default=None, foreign_key="app_user.id")
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = utc_field(default_factory=utcnow)

class JobInterviewer(SQLModel, table=True):
    """Users who usually interview for a job; the booking dialog offers them first."""
    __tablename__ = "job_interviewer"

    job_id: int = Field(foreign_key="job.id", primary_key=True)
    user_id: int = Field(foreign_key="app_user.id", primary_key=True)
