"""Login request and who-am-I shapes."""

from pydantic import BaseModel

from app.modules.users.schemas import UserBrief


class LoginIn(BaseModel):
    email: str
    password: str


class MeOut(UserBrief):
    google_connected: bool = False
