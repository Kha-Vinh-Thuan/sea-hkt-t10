"""Login route (email + password for a bearer token) and who-am-I."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth import service
from app.modules.auth.dependencies import require_user
from app.modules.auth.schemas import LoginIn, MeOut
from app.modules.google import service as google_service
from app.modules.users.models import User
from app.modules.users.schemas import UserBrief

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(data: LoginIn, request: Request, session: Session = Depends(get_session)):
    client = request.client.host if request.client else ""
    try:
        result = service.login(session, data.email, data.password, client)
    except service.AuthNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    except service.TooManyAttempts as e:
        raise HTTPException(429, str(e)) from e
    if not result:
        raise HTTPException(401, "Wrong email or password")
    token, user = result
    return {"token": token, "email": user.email, "user": UserBrief.model_validate(user, from_attributes=True)}

@router.get("/me", response_model=MeOut)
def me(user: User = Depends(require_user), session: Session = Depends(get_session)):
    return MeOut(**UserBrief.model_validate(user, from_attributes=True).model_dump(),
                 google_connected=google_service.is_connected(session, user.id))
