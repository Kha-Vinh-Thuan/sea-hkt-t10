"""Demo jobs so the careers site is not empty. Run once: python -m app.seed  (skips if jobs already exist)."""

from dotenv import load_dotenv

load_dotenv()

from sqlmodel import Session, select  # noqa: E402

from app.core.db import create_tables, engine  # noqa: E402
from app.models import Job  # noqa: E402

JOBS = [
    Job(
        title="Backend Developer",
        department="Engineering",
        location="Ho Chi Minh City / Hybrid",
        interview_duration_minutes=45,
        openings=2,
        description=(
            "Build and maintain reliable, secure and scalable backend services. Design REST APIs, work with "
            "relational databases, write tested code, and ship through CI/CD in an Agile/Scrum team."
        ),
        requirements=(
            "- Java or another backend language, OOP\n"
            "- REST APIs, HTTP, web development\n"
            "- SQL and relational database design\n"
            "- Agile/Scrum\n"
            "- Basic cloud, Docker, Git, CI/CD"
        ),
    ),
    Job(
        title="Frontend Developer",
        department="Engineering",
        location="Ho Chi Minh City",
        interview_duration_minutes=45,
        description="Build fast, accessible web interfaces with React and TypeScript, working closely with design.",
        requirements="- React, TypeScript\n- HTML/CSS, responsive layout\n- REST API integration\n- Git",
    ),
    Job(
        title="HR Executive",
        department="People",
        location="Ho Chi Minh City",
        interview_duration_minutes=30,
        description="Run day-to-day recruiting: screen candidates, coordinate interviews, keep the pipeline moving.",
        requirements="- 1+ year in recruiting or HR\n- Clear written and spoken communication\n- Organized, detail-oriented",
    ),
]

if __name__ == "__main__":
    create_tables()
    with Session(engine) as session:
        if session.exec(select(Job)).first():
            print("Jobs already exist, skipping seed.")
        else:
            session.add_all(JOBS)
            session.commit()
            print(f"Seeded {len(JOBS)} jobs.")
