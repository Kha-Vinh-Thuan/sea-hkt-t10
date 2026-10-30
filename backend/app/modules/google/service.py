"""Connect / disconnect a user's Google Calendar (OAuth2 authorization code + refresh token).

The `state` sent to Google is HMAC-signed with SECRET_KEY and carries the user id + expiry, so the callback
(which has no login header: it is a browser redirect from Google) knows whose token it stores and that we started it.
"""

import hashlib
import hmac
import time

from sqlmodel import Session

from app.config import settings
from app.integrations import google_calendar
from app.integrations.google_calendar import GoogleError
from app.modules.google import repository
from app.modules.google.models import GoogleCredential
from app.modules.users.models import User
from app.utils.errors import Invalid

STATE_TTL_SECONDS = 10 * 60

def _sign(payload: str) -> str:
    secret = settings.secret_key()
    if not secret:
        raise Invalid("SECRET_KEY is not set")
    # Prefixed so a login token signature can never be replayed as a state (and the other way round).
    return hmac.new(secret.encode(), f"google-state|{payload}".encode(), hashlib.sha256).hexdigest()

def make_state(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + STATE_TTL_SECONDS}"
    return f"{payload}.{_sign(payload)}"

def read_state(state: str) -> int:
    """User id inside a valid, unexpired state, else Invalid."""
    try:
        user_id, expires, signature = state.split(".")
        valid = hmac.compare_digest(signature, _sign(f"{user_id}.{expires}")) and int(expires) >= time.time()
    except ValueError:
        valid = False
    if not valid:
        raise Invalid("Invalid or expired Google sign-in state, please try again")
    return int(user_id)

def connect_url(user: User) -> str:
    if not google_calendar.configured():
        raise Invalid("Google Calendar is not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)")
    return google_calendar.consent_url(make_state(user.id))

def finish_connect(session: Session, state: str, code: str) -> None:
    """Callback: check state, swap the code for a refresh token, store it (replacing an older one)."""
    user_id = read_state(state)
    refresh_token, email = google_calendar.exchange_code(code)
    credential = repository.get(session, user_id) or GoogleCredential(user_id=user_id, refresh_token="")
    credential.refresh_token, credential.email = refresh_token, email
    session.add(credential)
    session.commit()

def disconnect(session: Session, user: User) -> None:
    credential = repository.get(session, user.id)
    if not credential:
        return
    try:
        google_calendar.revoke(credential.refresh_token)
    except GoogleError:
        pass  # forgetting the token locally is what matters; the user can also revoke it in their Google account
    session.delete(credential)
    session.commit()

def is_connected(session: Session, user_id: int) -> bool:
    return repository.get(session, user_id) is not None

def refresh_token_for(session: Session, user_id: int) -> str | None:
    credential = repository.get(session, user_id)
    return credential.refresh_token if credential else None

def refresh_token_for_email(session: Session, email: str) -> str | None:
    """Interviews store the interviewer by email; outsiders typed in by hand have no account, so None."""
    return repository.refresh_token_by_email(session, email)
