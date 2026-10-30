"""User routes: lightweight picker list for recruiters, full management for admins."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_admin, require_recruiter
from app.modules.users import service
from app.modules.users.models import Role, User
from app.modules.users.schemas import PasswordIn, UserBrief, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_recruiter)])
admin_router = APIRouter(prefix="/api/admin/users", tags=["users"])

@router.get("", response_model=list[UserBrief])
def list_active_users(role: Role | None = None, session: Session = Depends(get_session)):
    return service.list_active(session, role)

@admin_router.get("", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def list_users(session: Session = Depends(get_session)):
    return service.list_all(session)

@admin_router.post("", response_model=UserOut, status_code=201, dependencies=[Depends(require_admin)])
def create_user(data: UserCreate, session: Session = Depends(get_session)):
    return service.create(session, data)

@admin_router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, admin: User = Depends(require_admin),
                session: Session = Depends(get_session)):
    return service.update(session, admin, user_id, data)

@admin_router.post("/{user_id}/password", response_model=UserOut, dependencies=[Depends(require_admin)])
def reset_password(user_id: int, data: PasswordIn, session: Session = Depends(get_session)):
    return service.reset_password(session, user_id, data.password)
