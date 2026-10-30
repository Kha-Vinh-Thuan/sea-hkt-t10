"""Job recruiter/manager (active users only) and tags (trimmed, deduped, public)."""

from tests.test_api import client, recruiter  # noqa: F401 (fixtures)
from tests.test_users import add_user

def test_job_recruiter_and_manager_must_be_active_users(recruiter):
    rec = add_user(recruiter, "rec@example.com", "recruiter")
    boss = add_user(recruiter, "boss@example.com", "interviewer")
    ok = recruiter.put("/api/jobs/1", json={"title": "Backend", "recruiter_id": rec["id"], "manager_id": boss["id"]})
    assert ok.status_code == 200, ok.text
    assert (ok.json()["recruiter_id"], ok.json()["manager_id"]) == (rec["id"], boss["id"])
    listed = next(j for j in recruiter.get("/api/jobs").json() if j["id"] == 1)
    assert listed["recruiter_id"] == rec["id"]

    assert recruiter.post("/api/jobs", json={"title": "X", "manager_id": 999}).status_code == 422
    recruiter.patch(f"/api/admin/users/{rec['id']}", json={"is_active": False})
    assert recruiter.post("/api/jobs", json={"title": "X", "recruiter_id": rec["id"]}).status_code == 422
    cleared = recruiter.put("/api/jobs/1", json={"title": "Backend"}).json()
    assert cleared["recruiter_id"] is None and cleared["manager_id"] is None

def test_job_tags_are_cleaned_and_public(recruiter):
    job = recruiter.post("/api/jobs", json={"title": "Tagged", "tags": [" Python ", "", "Python", "Remote"]}).json()
    assert job["tags"] == ["Python", "Remote"]
    public = recruiter.get(f"/api/public/jobs/{job['id']}").json()
    assert public["tags"] == ["Python", "Remote"]
    assert recruiter.get("/api/public/jobs/1").json()["tags"] == []
