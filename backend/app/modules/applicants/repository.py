"""Applicant, attachment and activity queries. Writes are added to the session; the service decides when to commit."""

import json
from collections import Counter

from sqlalchemy import String, cast, or_
from sqlmodel import Session, func, select

from app.modules.applicants.models import Activity, Applicant, ApplicantAttachment, Stage


def get(session: Session, applicant_id: int) -> Applicant | None:
    return session.get(Applicant, applicant_id)


def find_by_job_and_email(session: Session, job_id: int, email: str) -> Applicant | None:
    return session.exec(select(Applicant).where(Applicant.job_id == job_id, Applicant.email == email)).first()


def list_same_person(session: Session, applicant: Applicant) -> list[Applicant]:
    """Other applications by the same email (any case) or the same non-empty phone, newest first."""
    match = func.lower(Applicant.email) == applicant.email.lower()
    if applicant.phone:
        match = or_(match, Applicant.phone == applicant.phone)
    query = select(Applicant).where(match, Applicant.id != applicant.id).order_by(Applicant.created_at.desc())
    return list(session.exec(query).all())


def list_by_job(session: Session, job_id: int | None, archived: bool = False, q: str = "",
                priority_min: int | None = None, tag: str = "", owner_id: int | None = None) -> list[Applicant]:
    query = select(Applicant).where(Applicant.archived == archived).order_by(Applicant.created_at.desc())
    if job_id is not None:
        query = query.where(Applicant.job_id == job_id)
    if owner_id is not None:
        query = query.where(Applicant.user_id == owner_id)
    if priority_min is not None:
        query = query.where(Applicant.priority >= priority_min)
    # tags is a JSON list: matched on its serialized text so it works on SQLite and Postgres alike.
    # ponytail: non-ASCII tags are stored as escaped unicode, so accented searches miss them; move to a
    # tag table (or Postgres jsonb @>) if that matters.
    tags_text = cast(Applicant.tags, String)
    term = q.strip()
    if term:
        query = query.where(or_(Applicant.name.icontains(term, autoescape=True),
                                Applicant.email.icontains(term, autoescape=True),
                                Applicant.cv_text.icontains(term, autoescape=True),
                                tags_text.icontains(term, autoescape=True)))
    if tag.strip():
        # The quoted JSON string matches a whole tag, not a substring of a longer one.
        query = query.where(tags_text.icontains(json.dumps(tag.strip()), autoescape=True))
    return list(session.exec(query).all())


def list_for_jobs(session: Session, job_ids: list[int]) -> list[Applicant]:
    """Every applicant of these jobs, archived included (reports count them too)."""
    return list(session.exec(select(Applicant).where(Applicant.job_id.in_(job_ids))).all())

def count_by_job(session: Session, stage: Stage | None = None) -> dict[int, int]:
    query = select(Applicant.job_id)
    if stage is not None:
        query = query.where(Applicant.stage == stage)
    return dict(Counter(session.exec(query).all()))


def add(session: Session, applicant: Applicant) -> Applicant:
    session.add(applicant)
    session.flush()  # assigns the id so the activity row can reference it
    return applicant


def add_activity(session: Session, applicant_id: int, message: str) -> None:
    session.add(Activity(applicant_id=applicant_id, message=message))


def list_activity(session: Session, applicant_id: int) -> list[Activity]:
    query = select(Activity).where(Activity.applicant_id == applicant_id).order_by(Activity.created_at, Activity.id)
    return list(session.exec(query).all())

def list_attachments(session: Session, applicant_id: int) -> list[ApplicantAttachment]:
    query = select(ApplicantAttachment).where(ApplicantAttachment.applicant_id == applicant_id)
    return list(session.exec(query.order_by(ApplicantAttachment.created_at, ApplicantAttachment.id)).all())

def get_attachment(session: Session, applicant_id: int, attachment_id: int) -> ApplicantAttachment | None:
    attachment = session.get(ApplicantAttachment, attachment_id)
    return attachment if attachment and attachment.applicant_id == applicant_id else None
