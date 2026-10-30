"""FastAPI dependencies other modules put on their routes: any signed-in user, staff (admin / recruiter), admin."""

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.service import AuthNotConfigured, current_user
from app.modules.users.models import Role, User
from app.modules.users.service import STAFF_ROLES

def require_user(authorization: str = Header(""), session: Session = Depends(get_session)) -> User:
    """The signed-in, active user, or 401."""
    scheme, _, token = authorization.partition(" ")
    try:
        user = current_user(session, token) if scheme.lower() == "bearer" else None
    except AuthNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    if not user:
        raise HTTPException(401, "Please sign in", headers={"WWW-Authenticate": "Bearer"})
    return user

def require_recruiter(user: User = Depends(require_user)) -> User:
    """Admin or recruiter; interviewers get 403."""
    if user.role not in STAFF_ROLES:
        raise HTTPException(403, "Recruiters only")
    return user

def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(403, "Admins only")
    return user
