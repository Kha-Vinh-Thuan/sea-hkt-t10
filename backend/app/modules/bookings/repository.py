"""slot_proposal queries."""

from sqlmodel import Session, select

from app.modules.bookings.models import SlotProposal

def get_by_token(session: Session, token: str) -> SlotProposal | None:
    return session.exec(select(SlotProposal).where(SlotProposal.token == token)).first()
