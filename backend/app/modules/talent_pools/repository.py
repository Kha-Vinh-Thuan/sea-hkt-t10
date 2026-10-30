"""Talent pool queries. Writes are added to the session; the service commits."""

from collections import Counter

from sqlmodel import Session, select

from app.modules.applicants.models import Applicant
from app.modules.talent_pools.models import TalentPool, TalentPoolMember

def get(session: Session, pool_id: int) -> TalentPool | None:
    return session.get(TalentPool, pool_id)

def list_all(session: Session) -> list[TalentPool]:
    return list(session.exec(select(TalentPool).order_by(TalentPool.name)).all())

def member_counts(session: Session) -> dict[int, int]:
    return dict(Counter(session.exec(select(TalentPoolMember.pool_id)).all()))

def get_member(session: Session, pool_id: int, applicant_id: int) -> TalentPoolMember | None:
    return session.get(TalentPoolMember, (pool_id, applicant_id))

def list_members(session: Session, pool_id: int) -> list[Applicant]:
    query = (select(Applicant).join(TalentPoolMember, TalentPoolMember.applicant_id == Applicant.id)
             .where(TalentPoolMember.pool_id == pool_id).order_by(Applicant.name))
    return list(session.exec(query).all())

def pool_ids_of(session: Session, applicant_id: int) -> list[int]:
    query = select(TalentPoolMember.pool_id).where(TalentPoolMember.applicant_id == applicant_id)
    return list(session.exec(query).all())

def delete_members(session: Session, pool_id: int) -> None:
    for member in session.exec(select(TalentPoolMember).where(TalentPoolMember.pool_id == pool_id)).all():
        session.delete(member)
