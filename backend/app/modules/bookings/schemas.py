"""Slot proposal request shapes. Times must carry a timezone."""

from pydantic import AwareDatetime, BaseModel, Field

class ProposalIn(BaseModel):
    interviewer_id: int
    slots: list[AwareDatetime] = Field(min_length=1, max_length=20)
    location: str = Field("", max_length=500)

class BookIn(BaseModel):
    start: AwareDatetime
