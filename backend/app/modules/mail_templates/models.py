"""mail_template table (Odoo mail.template): editable candidate email texts with {name} / {job} / {company} placeholders."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.modules.applicants.models import Stage
from app.utils.time import utc_field, utcnow

class MailTemplate(SQLModel, table=True):
    __tablename__ = "mail_template"

    id: int | None = Field(default=None, primary_key=True)
    # Set only on the seeded templates the app sends by itself (interest, refusal, ...); custom ones have none.
    key: str | None = Field(default=None, unique=True)
    name: str = ""
    subject: str = ""
    body: str = ""
    # The board offers this template when an applicant is moved into this stage.
    stage: Stage | None = None
    created_at: datetime = utc_field(default_factory=utcnow)
    updated_at: datetime = utc_field(default_factory=utcnow)
