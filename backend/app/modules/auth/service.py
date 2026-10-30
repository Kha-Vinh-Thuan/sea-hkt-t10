"""Recruiter login: one account from env, signed bearer token (stdlib HMAC, no extra dependency).

ponytail: single env account with a plaintext password; add a users table with hashed passwords and
rate-limited login once there is more than one recruiter or the app leaves localhost.
"""

import base64
import hashlib
import hmac
import time

from app.config import settings

TOKEN_TTL_SECONDS = 12 * 3600


class AuthNotConfigured(Exception):
    pass


def _sign(payload: str) -> str:
    secret = settings.secret_key()
    if not secret:
        raise AuthNotConfigured("SECRET_KEY is not set")
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(email: str) -> str:
    payload = f"{email}|{int(time.time()) + TOKEN_TTL_SECONDS}"
    return base64.urlsafe_b64encode(payload.encode()).decode() + "." + _sign(payload)


def verify_token(token: str) -> str | None:
    """Email of a valid, unexpired token, else None."""
    try:
        encoded, signature = token.split(".")
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
        email, expires = payload.rsplit("|", 1)
        expired = int(expires) < time.time()
    except ValueError:
        return None
    if expired or not hmac.compare_digest(signature, _sign(payload)):
        return None
    return email


def login(email: str, password: str) -> str | None:
    """A token if the credentials match the env account, else None."""
    expected_email, expected_password = settings.recruiter_account()
    if not expected_email or not expected_password:
        raise AuthNotConfigured("RECRUITER_EMAIL / RECRUITER_PASSWORD are not set")
    # Compare both in constant time so the response time does not reveal which one was wrong.
    email_ok = hmac.compare_digest(email.strip().lower().encode(), expected_email.lower().encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return make_token(expected_email) if email_ok and password_ok else None
