"""Talent pool rules: unique pool names, add / remove applicants (idempotent, logged), members with their job title."""

from sqlmodel import Session

from app.modules.applicants import repository as applicant_repo
from app.modules.applicants import service as applicant_service
from app.modules.jobs import service as job_service
from app.modules.talent_pools import repository
from app.modules.talent_pools.models import TalentPool, TalentPoolMember
from app.modules.talent_pools.schemas import PoolIn
from app.utils.errors import Conflict, NotFound

def get(session: Session, pool_id: int) -> TalentPool:
    pool = repository.get(session, pool_id)
    if not pool:
        raise NotFound("Talent pool not found")
    return pool

def _check_name(session: Session, name: str, pool_id: int | None = None) -> str:
    name = name.strip()
    if any(p.name.lower() == name.lower() and p.id != pool_id for p in repository.list_all(session)):
        raise Conflict("A talent pool with this name already exists")
    return name

def list_pools(session: Session) -> list[dict]:
    counts = repository.member_counts(session)
    return [{**p.model_dump(), "member_count": counts.get(p.id, 0)} for p in repository.list_all(session)]

def create(session: Session, data: PoolIn) -> TalentPool:
    pool = TalentPool(name=_check_name(session, data.name), description=data.description.strip())
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool

def update(session: Session, pool_id: int, data: PoolIn) -> TalentPool:
    pool = get(session, pool_id)
    pool.name = _check_name(session, data.name, pool_id)
    pool.description = data.description.strip()
    session.commit()
    session.refresh(pool)
    return pool

def delete(session: Session, pool_id: int) -> None:
    """Deletes the pool and its memberships; the applicants stay."""
    pool = get(session, pool_id)
    repository.delete_members(session, pool_id)
    session.flush()  # members first, or the foreign key blocks deleting the pool
    session.delete(pool)
    session.commit()

def members(session: Session, pool_id: int) -> list[dict]:
    get(session, pool_id)
    return [{"id": a.id, "name": a.name, "email": a.email, "job_id": a.job_id,
             "job_title": job_service.get(session, a.job_id).title, "stage": a.stage}
            for a in repository.list_members(session, pool_id)]

def add_member(session: Session, pool_id: int, applicant_id: int) -> None:
    pool = get(session, pool_id)
    applicant_service.get(session, applicant_id)
    if not repository.get_member(session, pool_id, applicant_id):
        session.add(TalentPoolMember(pool_id=pool_id, applicant_id=applicant_id))
        applicant_repo.add_activity(session, applicant_id, f"Added to talent pool: {pool.name}")
        session.commit()

def remove_member(session: Session, pool_id: int, applicant_id: int) -> None:
    pool = get(session, pool_id)
    member = repository.get_member(session, pool_id, applicant_id)
    if member:
        session.delete(member)
        applicant_repo.add_activity(session, applicant_id, f"Removed from talent pool: {pool.name}")
        session.commit()

def pools_of(session: Session, applicant_id: int) -> list[int]:
    """Ids of the pools the applicant is in (drawer)."""
    applicant_service.get(session, applicant_id)
    return repository.pool_ids_of(session, applicant_id)
