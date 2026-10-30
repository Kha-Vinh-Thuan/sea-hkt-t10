"""Job table."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow


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
    created_at: datetime = utc_field(default_factory=utcnow)
