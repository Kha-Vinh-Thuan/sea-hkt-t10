"""Talent pool request shapes."""

from pydantic import BaseModel, Field

class PoolIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field("", max_length=2000)

class MemberIn(BaseModel):
    applicant_id: int
