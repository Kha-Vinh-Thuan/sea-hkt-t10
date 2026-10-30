"""UTC helpers shared by every module's models and services."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    # SQLite hands back naive datetimes; everything is stored as UTC, so naive means UTC.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def utc_field(**kwargs: Any) -> Any:
    # timestamptz in Postgres, so the API returns "+00:00" and browsers show the right local time.
    return Field(sa_type=DateTime(timezone=True), **kwargs)
