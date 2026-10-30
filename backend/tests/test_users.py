"""Users + roles: hashing, bootstrap admin, admin-only routes, interviewer limits, last-admin rule, job interviewers."""

from datetime import timedelta

from sqlmodel import Session

from app.config.database import get_session
from app.main import app
from app.modules.interviews.models import Interview
from app.modules.users.passwords import hash_password, verify_password
from app.utils.time import utcnow
from tests.test_api import LOGIN, apply, client, recruiter, sent, tomorrow_at  # noqa: F401 (fixtures)

PASSWORD = "secret-pw-1"

def add_user(admin, email, role, name=""):
    response = admin.post("/api/admin/users", json={"email": email, "name": name, "role": role, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()

def token_for(client, email):
    return {"Authorization": "Bearer " + client.post("/api/auth/login",
                                                     json={"email": email, "password": PASSWORD}).json()["token"]}

def past_interview(applicant_id, email):
    session: Session = next(app.dependency_overrides[get_session]())
    start = utcnow() - timedelta(hours=2)
    interview = Interview(applicant_id=applicant_id, interviewer_email=email, start=start,
                          end=start + timedelta(minutes=45))
    session.add(interview)
    session.commit()
    return interview.id

def test_password_hash_round_trip():
    stored = hash_password("pw-123456")
    assert stored != hash_password("pw-123456")  # random salt
    assert verify_password("pw-123456", stored) and not verify_password("wrong", stored)
    assert not verify_password("pw-123456", "garbage")

def test_bootstrap_admin_logs_in_and_me(client):
    body = client.post("/api/auth/login", json=LOGIN).json()
    assert body["user"]["role"] == "admin"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"}).json()
    assert (me["email"], me["role"]) == (LOGIN["email"], "admin")
    assert "password_hash" not in me

def test_recruiter_cannot_use_admin_routes(recruiter):
    add_user(recruiter, "rec@example.com", "recruiter")
    headers = token_for(recruiter, "rec@example.com")
    assert recruiter.get("/api/admin/users", headers=headers).status_code == 403
    assert recruiter.post("/api/admin/users", headers=headers,
                          json={"email": "x@example.com", "role": "admin", "password": PASSWORD}).status_code == 403
    assert recruiter.get("/api/jobs", headers=headers).status_code == 200
    assert [u["email"] for u in recruiter.get("/api/users?role=recruiter", headers=headers).json()] == ["rec@example.com"]

def test_interviewer_sees_and_scores_only_own_interviews(recruiter, sent):
    add_user(recruiter, "ivy@example.com", "interviewer")
    applicant_id = apply(recruiter).json()["id"]
    mine = past_interview(applicant_id, "Ivy@example.com")
    other = past_interview(applicant_id, "marc@example.com")
    headers = token_for(recruiter, "ivy@example.com")

    assert [i["id"] for i in recruiter.get("/api/interviews", headers=headers).json()] == [mine]
    done = {"status": "done", "score": 4}
    assert recruiter.post(f"/api/interviews/{mine}/feedback", headers=headers, json=done).status_code == 200
    assert recruiter.post(f"/api/interviews/{other}/feedback", headers=headers, json=done).status_code == 403
    assert recruiter.get("/api/applicants", headers=headers).status_code == 403
    assert recruiter.get("/api/jobs", headers=headers).status_code == 403
    assert recruiter.post(f"/api/applicants/{applicant_id}/interviews", headers=headers,
                          json={"start": tomorrow_at(3), "interviewer_email": "ivy@example.com"}).status_code == 403
    # Recruiters/admins still score anyone's interview.
    assert recruiter.post(f"/api/interviews/{other}/feedback", json=done).status_code == 200

def test_last_admin_and_self_protection(recruiter):
    me = recruiter.get("/api/auth/me").json()
    assert recruiter.patch(f"/api/admin/users/{me['id']}", json={"role": "recruiter"}).status_code == 409
    assert recruiter.patch(f"/api/admin/users/{me['id']}", json={"is_active": False}).status_code == 409
    other = add_user(recruiter, "boss@example.com", "admin")
    # Another admin can be demoted while I remain; then I am the last one again.
    assert recruiter.patch(f"/api/admin/users/{other['id']}", json={"role": "recruiter"}).json()["role"] == "recruiter"
    assert recruiter.patch(f"/api/admin/users/{me['id']}", json={"name": "Root"}).json()["name"] == "Root"
    assert recruiter.post("/api/admin/users", json={"email": "boss@example.com", "role": "admin",
                                                    "password": PASSWORD}).status_code == 409

def test_deactivated_user_token_rejected_and_password_reset(recruiter):
    user = add_user(recruiter, "rec@example.com", "recruiter")
    headers = token_for(recruiter, "rec@example.com")
    assert recruiter.patch(f"/api/admin/users/{user['id']}", json={"is_active": False}).status_code == 200
    assert recruiter.get("/api/jobs", headers=headers).status_code == 401
    assert recruiter.post("/api/auth/login", json={"email": "rec@example.com", "password": PASSWORD}).status_code == 401

    recruiter.patch(f"/api/admin/users/{user['id']}", json={"is_active": True})
    assert recruiter.post(f"/api/admin/users/{user['id']}/password", json={"password": "new-pass-99"}).status_code == 200
    assert recruiter.post("/api/auth/login", json={"email": "rec@example.com", "password": "new-pass-99"}).status_code == 200

def test_job_interviewer_ids_validated_and_returned(recruiter):
    ivy = add_user(recruiter, "ivy@example.com", "interviewer")
    gone = add_user(recruiter, "gone@example.com", "interviewer")
    recruiter.patch(f"/api/admin/users/{gone['id']}", json={"is_active": False})

    created = recruiter.post("/api/jobs", json={"title": "QA", "interviewer_ids": [ivy["id"], ivy["id"]]})
    assert created.status_code == 201 and created.json()["interviewer_ids"] == [ivy["id"]]
    job_id = created.json()["id"]
    assert recruiter.put(f"/api/jobs/{job_id}", json={"title": "QA", "interviewer_ids": [gone["id"]]}).status_code == 422
    assert recruiter.put(f"/api/jobs/{job_id}", json={"title": "QA", "interviewer_ids": [999]}).status_code == 422
    # Omitting interviewer_ids keeps the list.
    assert recruiter.put(f"/api/jobs/{job_id}", json={"title": "QA 2"}).json()["interviewer_ids"] == [ivy["id"]]
    listed = next(j for j in recruiter.get("/api/jobs").json() if j["id"] == job_id)
    assert listed["interviewer_ids"] == [ivy["id"]]
