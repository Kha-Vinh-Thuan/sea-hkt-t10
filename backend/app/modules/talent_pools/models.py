"""Talent pool tables (Odoo hr.talent.pool, simplified): named groups of applicants to contact again later."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow

class TalentPool(SQLModel, table=True):
    __tablename__ = "talent_pool"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = utc_field(default_factory=utcnow)

class TalentPoolMember(SQLModel, table=True):
    __tablename__ = "talent_pool_member"

    pool_id: int = Field(foreign_key="talent_pool.id", primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", primary_key=True)
