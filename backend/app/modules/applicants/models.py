"""Applicant, attachment and activity-log tables, plus the fixed pipeline stages."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.utils.time import utc_field, utcnow


class Stage(StrEnum):
    # Fixed pipeline; order here is the column order on the board.
    new = "new"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"

# Odoo rotting_threshold_days, simplified: days in a stage before the card counts as stuck. None = never.
# ASSUMPTION: thresholds not in a product spec yet.
STUCK_AFTER_DAYS: dict[Stage, int | None] = {
    Stage.new: 3, Stage.screening: 5, Stage.interview: 7, Stage.offer: 5, Stage.hired: None, Stage.rejected: None,
}

# Odoo stage `requirements`: what must be true before the card leaves the stage. Shown in the drawer, not enforced.
# ASSUMPTION: texts not in a product spec yet.
STAGE_REQUIREMENTS: dict[Stage, str] = {
    Stage.new: "CV read; applicant matches the basic job requirements.",
    Stage.screening: "Phone screen done; salary expectation and availability noted.",
    Stage.interview: "All interviews done and every interviewer has left feedback.",
    Stage.offer: "Offer sent and accepted in writing by the applicant.",
    Stage.hired: "",
    Stage.rejected: "",
}

class Source(StrEnum):
    # Odoo UTM source, simplified to one fixed list. ASSUMPTION: list not in a product spec yet.
    careers_site = "careers_site"
    linkedin = "linkedin"
    referral = "referral"
    job_board = "job_board"
    other = "other"

class RefuseReason(StrEnum):
    # Same list as Odoo's refuse wizard.
    does_not_fit = "does_not_fit"
    refused_job_fit = "refused_job_fit"      # refused by the applicant: job fit
    refused_salary = "refused_salary"        # refused by the applicant: salary
    job_filled = "job_filled"
    duplicate = "duplicate"
    spam = "spam"


class Applicant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    name: str
    email: str = Field(index=True)
    phone: str = ""
    stage: Stage = Stage.new
    cv_filename: str = ""   # original name, shown to recruiters
    cv_path: str = ""       # stored_file key (random, never derived from user input); shared by copies
    cv_text: str = ""       # extracted text, read by recruiters and later by the Filter agent
    linkedin: str = ""
    short_intro: str = ""   # written by the candidate on the apply form
    notes: str = ""         # recruiter's own notes, never shown to the candidate
    priority: int = 0       # 0-3 stars
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    available_from: date | None = None
    degree: str = ""
    # ASSUMPTION: gross per month in VND, same unit as the job salary range.
    salary_expected: int | None = None
    salary_proposed: int | None = None
    archived: bool = False  # hidden from the board; restore puts it back in `new`
    refuse_reason: RefuseReason | None = None
    refused_at: datetime | None = utc_field(default=None)
    source: Source = Source.careers_site
    source_detail: str = ""  # free text, e.g. the referrer's name
    next_action: str = ""    # recruiter's next step (Odoo mail.activity, simplified)
    next_action_due: date | None = None
    next_action_user_id: int | None = Field(default=None, foreign_key="app_user.id")  # who does the next step
    user_id: int | None = Field(default=None, foreign_key="app_user.id", index=True)  # recruiter owner (Odoo user_id)
    stage_changed_at: datetime = utc_field(default_factory=utcnow)
    hired_at: datetime | None = utc_field(default=None)  # Odoo date_closed: set entering `hired`, cleared leaving it
    created_at: datetime = utc_field(default_factory=utcnow)


class ApplicantAttachment(SQLModel, table=True):
    # Files other than the CV (Odoo attachment_ids): portfolio, certificates, ID scans.
    __tablename__ = "applicant_attachment"

    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    filename: str           # original name, shown to recruiters
    stored_path: str        # stored_file key (random, never derived from user input)
    content_type: str       # from the checked extension, not the client
    size: int
    created_at: datetime = utc_field(default_factory=utcnow)

class Activity(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    message: str
    created_at: datetime = utc_field(default_factory=utcnow)
