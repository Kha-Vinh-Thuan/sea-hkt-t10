"""FastAPI dependency other modules put on their recruiter-only routes."""

from fastapi import Header, HTTPException

from app.modules.auth.service import AuthNotConfigured, verify_token


def require_recruiter(authorization: str = Header("")) -> str:
    """The signed-in recruiter's email, or 401."""
    scheme, _, token = authorization.partition(" ")
    try:
        email = verify_token(token) if scheme.lower() == "bearer" else None
    except AuthNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    if not email:
        raise HTTPException(401, "Please sign in", headers={"WWW-Authenticate": "Bearer"})
    return email
