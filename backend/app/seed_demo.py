"""Demo team and pipeline for manual testing: 3 admins, 3 interviewers, applicants in every stage, interviews.

Run after `python -m app.seed` (needs the demo jobs): python -m app.seed_demo  (skips if the demo users exist).
Rows are inserted directly, so no email is sent. All addresses are @example.com. Password: DEMO_PASSWORD from the
environment, else a random one printed once.
"""

import os
import secrets
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.config import settings
from app.config.database import engine, migrate
from app.modules.applicants.models import Activity, Applicant, RefuseReason, Source, Stage
from app.modules.files import repository as files
from app.modules.interviews.models import Interview, InterviewStatus, Recommendation
from app.modules.jobs.models import Job, JobInterviewer
from app.modules.users.models import Role, User
from app.modules.users.passwords import hash_password
from app.utils.time import utcnow

ADMINS = [("admin1@example.com", "An Admin"), ("admin2@example.com", "Binh Admin"), ("admin3@example.com", "Chi Admin")]
INTERVIEWERS = [("techlead1@example.com", "Duc Techlead"), ("techlead2@example.com", "Em Techlead"),
                ("techlead3@example.com", "Giang Techlead")]

# (job title, name, stage, source, priority, tags, extra)
APPLICANTS = [
    ("Backend Developer", "Hoang Nguyen", Stage.new, Source.careers_site, 0, ["python"], {}),
    ("Backend Developer", "Khanh Tran", Stage.new, Source.linkedin, 2, ["java", "spring"], {}),
    ("Backend Developer", "Lan Pham", Stage.screening, Source.referral, 3, ["python", "fastapi"],
     {"source_detail": "Referred by Duc"}),
    ("Backend Developer", "Minh Le", Stage.interview, Source.job_board, 2, ["go"], {}),
    ("Backend Developer", "Nam Vo", Stage.interview, Source.careers_site, 1, ["python"], {}),
    ("Backend Developer", "Oanh Do", Stage.offer, Source.linkedin, 3, ["java"], {"salary_expected": 30_000_000,
                                                                               "salary_proposed": 28_000_000}),
    ("Backend Developer", "Phuc Bui", Stage.hired, Source.referral, 3, ["python"], {}),
    ("Backend Developer", "Quang Ho", Stage.rejected, Source.careers_site, 0, [],
     {"refuse_reason": RefuseReason.does_not_fit}),
    ("Frontend Developer", "Rin Dang", Stage.new, Source.careers_site, 1, ["react"], {}),
    ("Frontend Developer", "Son Ngo", Stage.screening, Source.linkedin, 2, ["react", "typescript"], {}),
    ("Frontend Developer", "Tam Ly", Stage.interview, Source.job_board, 2, ["vue"], {}),
    ("Frontend Developer", "Uyen Mai", Stage.new, Source.other, 0, [], {"archived": True}),
    ("HR Executive", "Vy Truong", Stage.new, Source.careers_site, 1, ["recruiting"], {}),
    ("HR Executive", "Xuan Cao", Stage.screening, Source.referral, 2, ["hr"], {}),
]

def cv_text(name: str, tags: list[str]) -> str:
    skills = ", ".join(tags) or "general office tools"
    return f"{name}\nSkills: {skills}\nExperience: 3 years building products in a small team.\nEducation: Bachelor of IT"

def next_weekday_at(days_ahead: int, hour: int) -> datetime:
    zone = ZoneInfo(settings.timezone_name())
    day = date.today() + timedelta(days=days_ahead)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.combine(day, time(hour), zone)

def seed(session: Session, password: str) -> None:
    users = {}
    for email, name in ADMINS:
        users[email] = User(email=email, name=name, role=Role.admin, password_hash=hash_password(password))
    for email, name in INTERVIEWERS:
        users[email] = User(email=email, name=name, role=Role.interviewer, password_hash=hash_password(password))
    session.add_all(users.values())
    session.flush()

    jobs = {job.title: job for job in session.exec(select(Job)).all()}
    leads = [users[email] for email, _ in INTERVIEWERS]
    for title, lead_ids in [("Backend Developer", [0, 1]), ("Frontend Developer", [1, 2]), ("HR Executive", [2])]:
        job = jobs[title]
        job.recruiter_id = users["admin1@example.com"].id
        for i in lead_ids:
            session.add(JobInterviewer(job_id=job.id, user_id=leads[i].id))

    now = utcnow()
    by_name = {}
    for title, name, stage, source, priority, tags, extra in APPLICANTS:
        email = name.lower().replace(" ", ".") + "@example.com"
        text = cv_text(name, tags)
        key = files.add(session, f"{name} CV.txt", "text/plain", text.encode(), ".txt")
        applicant = Applicant(job_id=jobs[title].id, name=name, email=email, phone=f"09000000{len(by_name):02d}", stage=stage,
                              source=source, priority=priority, tags=tags, cv_filename=f"{name} CV.txt", cv_path=key,
                              cv_text=text, stage_changed_at=now - timedelta(days=len(by_name) % 9),
                              user_id=users["admin1@example.com"].id, **extra)
        if stage == Stage.hired:
            applicant.hired_at = now - timedelta(days=2)
        if stage == Stage.rejected:
            applicant.refused_at = now - timedelta(days=1)
        session.add(applicant)
        session.flush()
        session.add(Activity(applicant_id=applicant.id, message="Applied (demo data)"))
        by_name[name] = applicant

    def interview(name: str, lead: User, start: datetime, **fields) -> None:
        minutes = jobs[next(t for t, n, *_ in APPLICANTS if n == name)].interview_duration_minutes
        session.add(Interview(applicant_id=by_name[name].id, interviewer_name=lead.name, interviewer_email=lead.email,
                              start=start, end=start + timedelta(minutes=minutes), location="Meeting room 1", **fields))

    interview("Minh Le", leads[0], next_weekday_at(1, 10))
    interview("Nam Vo", leads[1], next_weekday_at(1, 14))
    interview("Tam Ly", leads[2], next_weekday_at(2, 9))
    interview("Oanh Do", leads[0], now - timedelta(days=3), status=InterviewStatus.done, score=4,
              recommendation=Recommendation.hire, feedback="Solid Java, clear communication.")
    session.commit()

if __name__ == "__main__":
    migrate()
    with Session(engine) as session:
        if not session.exec(select(Job)).first():
            raise SystemExit("No jobs yet: run `python -m app.seed` first.")
        if session.exec(select(User).where(User.email == ADMINS[0][0])).first():
            raise SystemExit("Demo users already exist, skipping.")
        password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(9)
        seed(session, password)
    print(f"Seeded {len(ADMINS)} admins, {len(INTERVIEWERS)} interviewers, {len(APPLICANTS)} applicants, 4 interviews.")
    if not os.environ.get("DEMO_PASSWORD"):
        print(f"Password for every demo account (shown once): {password}")
