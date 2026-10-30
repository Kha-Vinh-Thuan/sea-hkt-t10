"""Interview request shape. `start` must carry a timezone so the stored instant is unambiguous."""

from pydantic import AwareDatetime, BaseModel, EmailStr, Field


class InterviewIn(BaseModel):
    start: AwareDatetime
    interviewer_name: str = Field("", max_length=200)
    interviewer_email: EmailStr
    location: str = Field("", max_length=500)
