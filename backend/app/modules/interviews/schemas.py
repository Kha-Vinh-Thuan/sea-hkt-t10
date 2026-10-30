"""Interview request shapes. `start` must carry a timezone so the stored instant is unambiguous."""

from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from app.modules.interviews.models import InterviewStatus, Recommendation

class InterviewIn(BaseModel):
    start: AwareDatetime
    interviewer_name: str = Field("", max_length=200)
    interviewer_email: EmailStr
    location: str = Field("", max_length=500)

class FeedbackIn(BaseModel):
    status: InterviewStatus   # the service accepts only done / no_show
    score: int | None = Field(None, ge=1, le=5)
    recommendation: Recommendation | None = None
    feedback: str = Field("", max_length=5000)
