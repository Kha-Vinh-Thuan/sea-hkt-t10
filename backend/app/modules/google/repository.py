"""google_credential queries."""

from sqlmodel import Session, func, select

from app.modules.google.models import GoogleCredential
from app.modules.users.models import User

def get(session: Session, user_id: int) -> GoogleCredential | None:
    return session.get(GoogleCredential, user_id)

def refresh_token_by_email(session: Session, email: str) -> str | None:
    query = (select(GoogleCredential.refresh_token).join(User, User.id == GoogleCredential.user_id)
             .where(func.lower(User.email) == email.strip().lower()))
    return session.exec(query).first()
