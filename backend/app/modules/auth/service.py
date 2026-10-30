"""Login against the users table, signed bearer token (stdlib HMAC, no extra dependency).

The token carries user id + role; every request reloads the user, so deactivation or a role change applies at once.
ponytail: no login rate limit; add one before the app leaves localhost.
"""

import base64
import hashlib
import hmac
import time

from sqlmodel import Session

from app.config import settings
from app.modules.users import service as users
from app.modules.users.models import User

TOKEN_TTL_SECONDS = 12 * 3600

class AuthNotConfigured(Exception):
    pass

def _sign(payload: str) -> str:
    secret = settings.secret_key()
    if not secret:
        raise AuthNotConfigured("SECRET_KEY is not set")
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def make_token(user: User) -> str:
    payload = f"{user.id}|{user.role}|{int(time.time()) + TOKEN_TTL_SECONDS}"
    return base64.urlsafe_b64encode(payload.encode()).decode() + "." + _sign(payload)

def verify_token(token: str) -> int | None:
    """User id of a valid, unexpired token, else None."""
    try:
        encoded, signature = token.split(".")
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
        user_id, _role, expires = payload.split("|")
        expired = int(expires) < time.time()
    except ValueError:
        return None
    if expired or not hmac.compare_digest(signature, _sign(payload)):
        return None
    return int(user_id)

def current_user(session: Session, token: str) -> User | None:
    """The active user behind a token; None if the token is bad or the user was deleted / deactivated."""
    user_id = verify_token(token)
    return users.get_active(session, user_id) if user_id is not None else None

def login(session: Session, email: str, password: str) -> tuple[str, User] | None:
    """(token, user) if the credentials match an active user, else None."""
    if not settings.secret_key():
        raise AuthNotConfigured("SECRET_KEY is not set")
    try:
        user = users.authenticate(session, email, password)
    except users.NotConfigured as e:
        raise AuthNotConfigured(str(e)) from e
    return (make_token(user), user) if user else None
