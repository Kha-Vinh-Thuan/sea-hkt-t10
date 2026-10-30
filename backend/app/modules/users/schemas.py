"""User request/response shapes. password_hash never leaves the server."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.models import Role

# ASSUMPTION: 8 characters minimum until the product spec sets a password policy.
Password = Annotated[str, Field(min_length=8, max_length=200)]

class UserBrief(BaseModel):
    """For pickers (interviewer select, job interviewers)."""
    id: int
    name: str
    email: str
    role: Role

class UserOut(UserBrief):
    is_active: bool
    created_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field("", max_length=200)
    role: Role
    password: Password

class UserUpdate(BaseModel):
    # Partial update: only fields sent are changed (exclude_unset).
    name: str = Field("", max_length=200)
    role: Role = Role.recruiter
    is_active: bool = True

class PasswordIn(BaseModel):
    password: Password
