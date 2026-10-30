"""Recruiter login: one account from env, signed bearer token (stdlib HMAC, no extra dependency).

ponytail: single env account with a plaintext password; add a users table with hashed passwords and
rate-limited login once there is more than one recruiter or the app leaves localhost.
"""

import base64
import hashlib
import hmac
import os
import time

from fastapi import Header, HTTPException

TOKEN_TTL_SECONDS = 12 * 3600


def _secret() -> bytes:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise HTTPException(503, "SECRET_KEY is not set")
    return secret.encode()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


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


def check_credentials(email: str, password: str) -> str | None:
    """The recruiter email if the credentials match the env account, else None."""
    expected_email = os.environ.get("RECRUITER_EMAIL", "")
    expected_password = os.environ.get("RECRUITER_PASSWORD", "")
    if not expected_email or not expected_password:
        raise HTTPException(503, "RECRUITER_EMAIL / RECRUITER_PASSWORD are not set")
    # Compare both in constant time so the response time does not reveal which one was wrong.
    email_ok = hmac.compare_digest(email.strip().lower().encode(), expected_email.lower().encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return expected_email if email_ok and password_ok else None


def require_recruiter(authorization: str = Header("")) -> str:
    """FastAPI dependency: the signed-in recruiter's email, or 401."""
    scheme, _, token = authorization.partition(" ")
    email = verify_token(token) if scheme.lower() == "bearer" else None
    if not email:
        raise HTTPException(401, "Please sign in", headers={"WWW-Authenticate": "Bearer"})
    return email
