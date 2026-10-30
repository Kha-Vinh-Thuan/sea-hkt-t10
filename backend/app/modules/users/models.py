"""User table and the three roles: admin manages users, recruiter runs hiring, interviewer only sees own interviews."""

from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow

class Role(StrEnum):
    admin = "admin"
    recruiter = "recruiter"
    interviewer = "interviewer"

class User(SQLModel, table=True):
    # "user" is a reserved word in Postgres (`select * from user` returns the DB login), so avoid it.
    __tablename__ = "app_user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)   # stored lowercase
    name: str = ""
    role: Role = Role.recruiter
    password_hash: str
    is_active: bool = True
    created_at: datetime = utc_field(default_factory=utcnow)
