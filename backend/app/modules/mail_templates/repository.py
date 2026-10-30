"""Mail template queries. Only this file talks to the mail_template table."""

from sqlmodel import Session, func, select

from app.modules.mail_templates.models import MailTemplate

def get(session: Session, template_id: int) -> MailTemplate | None:
    return session.get(MailTemplate, template_id)

def get_by_key(session: Session, key: str) -> MailTemplate | None:
    return session.exec(select(MailTemplate).where(MailTemplate.key == key)).first()

def list_all(session: Session) -> list[MailTemplate]:
    return list(session.exec(select(MailTemplate).order_by(MailTemplate.name, MailTemplate.id)).all())

def count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(MailTemplate)).one()

def save(session: Session, template: MailTemplate) -> MailTemplate:
    session.add(template)
    session.commit()
    session.refresh(template)
    return template

def delete(session: Session, template: MailTemplate) -> None:
    session.delete(template)
    session.commit()
