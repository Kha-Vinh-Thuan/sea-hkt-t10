"""API tests on in-memory SQLite: apply flow, login, board, stage moves, interviews + invitation email."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.modules.interviews import service as interviews
from app.config.database import get_session
from app.main import app
from app.modules.jobs import service as jobs_service
from app.modules.jobs.models import Job

LOGIN = {"email": "hr@example.com", "password": "pw"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("RECRUITER_EMAIL", LOGIN["email"])
    monkeypatch.setenv("RECRUITER_PASSWORD", LOGIN["password"])
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Job(id=1, title="Backend Developer", interview_duration_minutes=45))
        session.add(Job(id=2, title="Closed role", is_open=False))
        session.commit()

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def recruiter(client):
    token = client.post("/api/auth/login", json=LOGIN).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def sent(monkeypatch):
    mails = []
    monkeypatch.setattr(interviews, "send_invite", lambda **kw: mails.append(kw))
    return mails


def apply(client, job_id=1, email="an@example.com", file=("cv.txt", b"Java, SQL, REST APIs")):
    return client.post(f"/api/public/jobs/{job_id}/apply",
                       data={"name": "An", "email": email}, files={"cv": file})


def tomorrow_at(hour: int) -> str:
    day = datetime.now(timezone.utc) + timedelta(days=1)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def test_public_jobs_hide_closed_roles_and_internal_fields(client):
    jobs = client.get("/api/public/jobs").json()
    assert [j["title"] for j in jobs] == ["Backend Developer"]
    assert "interview_duration_minutes" not in jobs[0]
    assert client.get("/api/public/jobs/2").status_code == 404


def test_apply_rejects_bad_input(client):
    assert apply(client, file=("cv.exe", b"MZ")).status_code == 422
    assert apply(client, file=("cv.pdf", b"not a pdf")).status_code == 422
    assert apply(client, email="not-an-email").status_code == 422
    assert apply(client, job_id=2).status_code == 404


def test_same_email_cannot_apply_twice_to_one_job(client):
    assert apply(client).status_code == 201
    assert apply(client).status_code == 409


def test_recruiter_endpoints_need_a_valid_login(client):
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/jobs", headers={"Authorization": "Bearer forged.token"}).status_code == 401
    assert client.post("/api/auth/login", json={**LOGIN, "password": "wrong"}).status_code == 401


def test_apply_then_recruiter_sees_cv_and_moves_stage(recruiter):
    applicant_id = apply(recruiter).json()["id"]

    board = recruiter.get("/api/applicants", params={"job_id": 1}).json()
    assert [a["id"] for a in board] == [applicant_id]
    assert "cv_text" not in board[0]
    assert {j["id"]: j["applicant_count"] for j in recruiter.get("/api/jobs").json()} == {1: 1, 2: 0}

    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert detail["cv_text"] == "Java, SQL, REST APIs"
    assert "cv_path" not in detail
    assert recruiter.get(f"/api/applicants/{applicant_id}/cv").content == b"Java, SQL, REST APIs"

    assert recruiter.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "screening"}).status_code == 200
    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert [a["message"] for a in detail["activity"]] == ["Applied through the careers site", "Interest email sent",
                                                     "Stage: new → screening"]
    assert recruiter.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "bogus"}).status_code == 422


def test_schedule_interview_uses_job_duration_emails_ics_and_moves_stage(recruiter, sent):
    applicant_id = apply(recruiter).json()["id"]
    body = {"start": tomorrow_at(3), "interviewer_name": "Marc", "interviewer_email": "marc@example.com",
            "location": "https://meet.example.com/abc"}

    result = recruiter.post(f"/api/applicants/{applicant_id}/interviews", json=body).json()

    assert result["emailed"] is True
    interview = result["interview"]
    start, end = datetime.fromisoformat(interview["start"]), datetime.fromisoformat(interview["end"])
    assert end - start == timedelta(minutes=45)
    assert sent[0]["to"] == ["an@example.com", "marc@example.com"]
    assert "BEGIN:VEVENT" in sent[0]["ics"] and "DTSTART:" in sent[0]["ics"]

    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert detail["stage"] == "interview"
    assert detail["activity"][-1]["message"] == "Invitation emailed"
    assert [i["applicant_name"] for i in recruiter.get("/api/interviews").json()] == ["An"]


def test_interview_rejects_past_time_and_interviewer_double_booking(recruiter, sent):
    first = apply(recruiter).json()["id"]
    second = apply(recruiter, email="binh@example.com").json()["id"]
    booking = {"start": tomorrow_at(3), "interviewer_email": "marc@example.com"}

    past = {**booking, "start": "2020-01-01T03:00:00+00:00"}
    assert recruiter.post(f"/api/applicants/{first}/interviews", json=past).status_code == 422
    assert recruiter.post(f"/api/applicants/{first}/interviews",
                          json={**booking, "start": "2030-01-01T03:00:00"}).status_code == 422  # no timezone
    assert recruiter.post(f"/api/applicants/{first}/interviews", json=booking).status_code == 201
    assert recruiter.post(f"/api/applicants/{second}/interviews", json=booking).status_code == 409


def test_mail_failure_keeps_the_booking_and_reports_it(recruiter, monkeypatch):
    def fail(**_kw):
        raise interviews.MailError("Could not send email: connection refused")

    monkeypatch.setattr(interviews, "send_invite", fail)
    applicant_id = apply(recruiter).json()["id"]
    result = recruiter.post(f"/api/applicants/{applicant_id}/interviews",
                            json={"start": tomorrow_at(3), "interviewer_email": "marc@example.com"}).json()

    assert result["emailed"] is False and "connection refused" in result["mail_error"]
    assert len(recruiter.get(f"/api/applicants/{applicant_id}").json()["interviews"]) == 1


def test_job_date_window_hides_job_from_public_and_blocks_apply(recruiter):
    today = jobs_service.today()
    past = {"title": "Expired", "closes_on": str(today - timedelta(days=1))}
    future = {"title": "Not yet", "opens_on": str(today + timedelta(days=1))}
    current = {"title": "Last day", "opens_on": str(today), "closes_on": str(today), "is_remote": True}
    ids = {body["title"]: recruiter.post("/api/jobs", json=body).json()["id"] for body in (past, future, current)}

    public = recruiter.get("/api/public/jobs").json()
    assert {j["title"] for j in public} == {"Backend Developer", "Last day"}
    assert next(j for j in public if j["title"] == "Last day")["is_remote"] is True
    for title in ("Expired", "Not yet"):
        assert recruiter.get(f"/api/public/jobs/{ids[title]}").status_code == 404
        assert apply(recruiter, job_id=ids[title]).status_code == 404
    assert apply(recruiter, job_id=ids["Last day"]).status_code == 201


def test_job_rejects_inverted_salary_and_date_ranges(recruiter):
    assert recruiter.post("/api/jobs", json={"title": "X", "salary_min": 20, "salary_max": 10}).status_code == 422
    assert recruiter.put("/api/jobs/1", json={"title": "X", "opens_on": "2030-02-01",
                                               "closes_on": "2030-01-01"}).status_code == 422
    assert recruiter.post("/api/jobs", json={"title": "X", "employment_type": "freelance"}).status_code == 422
    ok = recruiter.put("/api/jobs/1", json={"title": "X", "salary_min": 10, "salary_max": 10,
                                             "employment_type": "internship"})
    assert ok.status_code == 200 and ok.json()["employment_type"] == "internship"


def test_recruiter_job_list_counts_hired(recruiter):
    hired = apply(recruiter).json()["id"]
    apply(recruiter, email="binh@example.com")
    recruiter.patch(f"/api/applicants/{hired}/stage", json={"stage": "hired"})
    job = next(j for j in recruiter.get("/api/jobs").json() if j["id"] == 1)
    assert (job["applicant_count"], job["hired_count"], job["openings"]) == (2, 1, 1)

def test_login_is_locked_after_repeated_failures(client):
    wrong = {**LOGIN, "password": "wrong"}
    assert [client.post("/api/auth/login", json=wrong).status_code for _ in range(6)] == [401] * 5 + [429]
    # Even the right password waits out the window; another email from the same client is unaffected.
    assert client.post("/api/auth/login", json=LOGIN).status_code == 429
    assert client.post("/api/auth/login", json={**wrong, "email": "other@example.com"}).status_code == 401
