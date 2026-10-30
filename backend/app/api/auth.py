"""Login route: exchange the recruiter's email + password for a bearer token."""

from fastapi import APIRouter, HTTPException

from app.core.security import check_credentials, make_token
from app.schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(data: LoginIn):
    email = check_credentials(data.email, data.password)
    if not email:
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(email), "email": email}
