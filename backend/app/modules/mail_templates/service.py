"""Mail template rules: seed the defaults into an empty table, admin CRUD, safe placeholder rendering."""

import re

from sqlmodel import Session

from app.config import settings
from app.modules.mail_templates import repository
from app.modules.mail_templates.defaults import DEFAULTS
from app.modules.mail_templates.models import MailTemplate
from app.modules.mail_templates.schemas import TemplateIn
from app.utils.errors import NotFound
from app.utils.time import utcnow

# Only a bare {word} is replaced, never str.format: "{name.__class__}" or "{0}" can not reach any attribute.
_PLACEHOLDER = re.compile(r"\{(\w+)\}")

def render(text: str, values: dict[str, str]) -> str:
    """Fill known placeholders; unknown ones stay as typed, so a typo shows in the mail instead of failing."""
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)

def placeholder_values(name: str, job: str) -> dict[str, str]:
    return {"name": name, "job": job, "company": settings.company_name()}

def ensure_defaults(session: Session) -> None:
    """First use: seed the default templates (like the bootstrap admin). Only runs on an empty table."""
    if repository.count(session):
        return
    for key, d in DEFAULTS.items():
        session.add(MailTemplate(key=key, name=d.name, subject=d.subject, body=d.body, stage=d.stage))
    session.commit()

def list_all(session: Session) -> list[MailTemplate]:
    ensure_defaults(session)
    return repository.list_all(session)

def get(session: Session, template_id: int) -> MailTemplate:
    template = repository.get(session, template_id)
    if not template:
        raise NotFound("Mail template not found")
    return template

def texts_for_key(session: Session, key: str) -> tuple[str, str]:
    """(subject, body) of the keyed template, else the code default (an admin deleted it)."""
    ensure_defaults(session)
    template = repository.get_by_key(session, key)
    return (template.subject, template.body) if template else (DEFAULTS[key].subject, DEFAULTS[key].body)

def create(session: Session, data: TemplateIn) -> MailTemplate:
    ensure_defaults(session)  # else the first custom template would stop the defaults from ever being seeded
    return repository.save(session, MailTemplate(**data.model_dump()))

def update(session: Session, template_id: int, data: TemplateIn) -> MailTemplate:
    template = get(session, template_id)
    template.sqlmodel_update(data.model_dump())
    template.updated_at = utcnow()
    return repository.save(session, template)

def delete(session: Session, template_id: int) -> None:
    repository.delete(session, get(session, template_id))
