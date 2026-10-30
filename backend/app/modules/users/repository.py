"""User queries. Only this file talks to the app_user table."""

from sqlmodel import Session, func, select

from app.modules.users.models import Role, User

def get(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)

def get_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()

def list_all(session: Session, role: Role | None = None, active_only: bool = False) -> list[User]:
    query = select(User).order_by(User.name, User.email)
    if role:
        query = query.where(User.role == role)
    if active_only:
        query = query.where(User.is_active)
    return list(session.exec(query).all())

def count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User)).one()

def count_active_admins(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User).where(User.role == Role.admin, User.is_active)).one()

def save(session: Session, user: User) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
