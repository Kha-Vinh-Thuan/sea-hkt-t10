"""Login request shape."""

from pydantic import BaseModel


class LoginIn(BaseModel):
    email: str
    password: str
