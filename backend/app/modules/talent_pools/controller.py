"""Talent pool routes: CRUD pools, add / remove / list members, pools of one applicant (drawer)."""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.talent_pools import service
from app.modules.talent_pools.schemas import MemberIn, PoolIn

router = APIRouter(prefix="/api", tags=["talent pools"], dependencies=[Depends(require_recruiter)])

@router.get("/talent-pools")
def list_pools(session: Session = Depends(get_session)):
    return service.list_pools(session)

@router.post("/talent-pools", status_code=201)
def create_pool(data: PoolIn, session: Session = Depends(get_session)):
    return service.create(session, data)

@router.put("/talent-pools/{pool_id}")
def update_pool(pool_id: int, data: PoolIn, session: Session = Depends(get_session)):
    return service.update(session, pool_id, data)

@router.delete("/talent-pools/{pool_id}", status_code=204)
def delete_pool(pool_id: int, session: Session = Depends(get_session)):
    service.delete(session, pool_id)
    return Response(status_code=204)

@router.get("/talent-pools/{pool_id}/members")
def list_members(pool_id: int, session: Session = Depends(get_session)):
    return service.members(session, pool_id)

@router.post("/talent-pools/{pool_id}/members", status_code=204)
def add_member(pool_id: int, data: MemberIn, session: Session = Depends(get_session)):
    service.add_member(session, pool_id, data.applicant_id)
    return Response(status_code=204)

@router.delete("/talent-pools/{pool_id}/members/{applicant_id}", status_code=204)
def remove_member(pool_id: int, applicant_id: int, session: Session = Depends(get_session)):
    service.remove_member(session, pool_id, applicant_id)
    return Response(status_code=204)

@router.get("/applicants/{applicant_id}/talent-pools")
def pools_of_applicant(applicant_id: int, session: Session = Depends(get_session)):
    return service.pools_of(session, applicant_id)
