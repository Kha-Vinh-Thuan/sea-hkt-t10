"""Mail template request shapes. `key` is not editable: only seeded templates have one."""

from pydantic import BaseModel, Field

from app.modules.applicants.models import Stage

class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field("", max_length=20000)
    stage: Stage | None = None

class ComposeIn(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
