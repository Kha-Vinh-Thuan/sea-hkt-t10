"""Login route: exchange the recruiter's email + password for a bearer token."""

from fastapi import APIRouter, HTTPException

from app.modules.auth import service
from app.modules.auth.schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(data: LoginIn):
    try:
        token = service.login(data.email, data.password)
    except service.AuthNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    if not token:
        raise HTTPException(401, "Wrong email or password")
    return {"token": token, "email": data.email.strip().lower()}
