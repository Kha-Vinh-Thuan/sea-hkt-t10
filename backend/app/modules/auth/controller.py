"""Login route (email + password for a bearer token) and who-am-I."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth import service
from app.modules.auth.dependencies import require_user
from app.modules.auth.schemas import LoginIn
from app.modules.users.models import User
from app.modules.users.schemas import UserBrief

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(data: LoginIn, session: Session = Depends(get_session)):
    try:
        result = service.login(session, data.email, data.password)
    except service.AuthNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    if not result:
        raise HTTPException(401, "Wrong email or password")
    token, user = result
    return {"token": token, "email": user.email, "user": UserBrief.model_validate(user, from_attributes=True)}

@router.get("/me", response_model=UserBrief)
def me(user: User = Depends(require_user)):
    return user
