"""Google account a user connected: the refresh token lets the server read free/busy and write calendar events."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow

class GoogleCredential(SQLModel, table=True):
    __tablename__ = "google_credential"

    user_id: int = Field(foreign_key="app_user.id", primary_key=True)
    # ponytail: stored in plain text like the DB password in .env; encrypt with a key from settings if the DB is shared.
    refresh_token: str
    email: str = ""   # the Google account, shown to the user
    created_at: datetime = utc_field(default_factory=utcnow)
