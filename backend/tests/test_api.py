"""API tests on in-memory SQLite: apply flow, validation, board, stage moves."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Job


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Job(id=1, title="Backend Developer"))
        session.add(Job(id=2, title="Closed role", is_open=False))
        session.commit()

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def apply(client, job_id=1, email="an@example.com", file=("cv.txt", b"Java, SQL, REST APIs")):
    return client.post(f"/api/public/jobs/{job_id}/apply",
                       data={"name": "An", "email": email}, files={"cv": file})


def test_public_jobs_hide_closed_roles_and_internal_fields(client):
    jobs = client.get("/api/public/jobs").json()
    assert [j["title"] for j in jobs] == ["Backend Developer"]
    assert "interview_duration_minutes" not in jobs[0]
    assert client.get("/api/public/jobs/2").status_code == 404


def test_apply_creates_applicant_with_cv_text_and_activity(client):
    response = apply(client)
    assert response.status_code == 201

    detail = client.get(f"/api/applicants/{response.json()['id']}").json()
    assert detail["stage"] == "new"
    assert detail["cv_text"] == "Java, SQL, REST APIs"
    assert "cv_path" not in detail
    assert detail["activity"][0]["message"] == "Applied through the careers site"
    assert client.get(f"/api/applicants/{detail['id']}/cv").content == b"Java, SQL, REST APIs"


def test_apply_rejects_bad_input(client):
    assert apply(client, file=("cv.exe", b"MZ")).status_code == 422
    assert apply(client, file=("cv.pdf", b"not a pdf")).status_code == 422
    assert apply(client, email="not-an-email").status_code == 422
    assert apply(client, job_id=2).status_code == 404


def test_same_email_cannot_apply_twice_to_one_job(client):
    assert apply(client).status_code == 201
    assert apply(client).status_code == 409


def test_board_lists_applicants_and_moves_stage_with_log(client):
    applicant_id = apply(client).json()["id"]

    board = client.get("/api/applicants", params={"job_id": 1}).json()
    assert [a["id"] for a in board] == [applicant_id]
    assert "cv_text" not in board[0]
    counts = {j["id"]: j["applicant_count"] for j in client.get("/api/jobs").json()}
    assert counts == {1: 1, 2: 0}

    assert client.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "screening"}).status_code == 200
    detail = client.get(f"/api/applicants/{applicant_id}").json()
    assert detail["stage"] == "screening"
    assert detail["activity"][-1]["message"] == "Stage: new → screening"
    assert client.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "bogus"}).status_code == 422
