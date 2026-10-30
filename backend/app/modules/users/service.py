"""User rules: bootstrap admin from env, credential check, admin management that never leaves the app without an admin."""

from sqlmodel import Session

from app.config import settings
from app.modules.users import repository
from app.modules.users.models import Role, User
from app.modules.users.passwords import hash_password, verify_password
from app.modules.users.schemas import UserCreate, UserUpdate
from app.utils.errors import Conflict, Invalid, NotFound

STAFF_ROLES = {Role.admin, Role.recruiter}

# Checked against when the email is unknown, so a wrong email costs the same time as a wrong password.
_DUMMY_HASH = hash_password("timing-equalizer")

class NotConfigured(Exception):
    pass

def normalize(email: str) -> str:
    return email.strip().lower()

def bootstrap_admin(session: Session) -> None:
    """First run: turn RECRUITER_EMAIL / RECRUITER_PASSWORD into the first admin, so the old .env keeps working."""
    if repository.count(session):
        return
    email, password = settings.recruiter_account()
    if not email or not password:
        raise NotConfigured("No users yet and RECRUITER_EMAIL / RECRUITER_PASSWORD are not set")
    repository.save(session, User(email=normalize(email), name="Admin", role=Role.admin,
                                  password_hash=hash_password(password)))

def authenticate(session: Session, email: str, password: str) -> User | None:
    bootstrap_admin(session)
    user = repository.get_by_email(session, normalize(email))
    password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    return user if user and password_ok and user.is_active else None

def get_active(session: Session, user_id: int) -> User | None:
    user = repository.get(session, user_id)
    return user if user and user.is_active else None

def get(session: Session, user_id: int) -> User:
    user = repository.get(session, user_id)
    if not user:
        raise NotFound("User not found")
    return user

def list_all(session: Session) -> list[User]:
    return repository.list_all(session)

def list_active(session: Session, role: Role | None = None) -> list[User]:
    return repository.list_all(session, role=role, active_only=True)

def check_active_ids(session: Session, user_ids: list[int]) -> list[int]:
    """Deduplicated ids, all of existing active users, else Invalid."""
    unique = list(dict.fromkeys(user_ids))
    missing = [i for i in unique if not get_active(session, i)]
    if missing:
        raise Invalid(f"Unknown or inactive users: {missing}")
    return unique

def create(session: Session, data: UserCreate) -> User:
    email = normalize(data.email)
    if repository.get_by_email(session, email):
        raise Conflict("A user with this email already exists")
    return repository.save(session, User(email=email, name=data.name.strip(), role=data.role,
                                         password_hash=hash_password(data.password)))

def update(session: Session, actor: User, user_id: int, data: UserUpdate) -> User:
    user = get(session, user_id)
    changes = data.model_dump(exclude_unset=True)
    loses_admin = user.role == Role.admin and user.is_active and (
        changes.get("role", Role.admin) != Role.admin or changes.get("is_active", True) is False)
    if loses_admin and user.id == actor.id:
        raise Conflict("You cannot deactivate or demote yourself")
    if loses_admin and repository.count_active_admins(session) <= 1:
        raise Conflict("At least one active admin must remain")
    if "name" in changes:
        changes["name"] = changes["name"].strip()
    user.sqlmodel_update(changes)
    return repository.save(session, user)

def reset_password(session: Session, user_id: int, password: str) -> User:
    user = get(session, user_id)
    user.password_hash = hash_password(password)
    return repository.save(session, user)
