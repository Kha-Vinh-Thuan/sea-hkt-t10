"""Hire date, reports summary, stage requirements and talent pools."""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine

from app.modules.applicants.models import Applicant, RefuseReason, Source, Stage
from app.modules.jobs.models import Job
from app.modules.reports import service as reports
from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)
from tests.test_applicant_extras import post_apply

def test_hired_at_set_on_hire_and_cleared_on_leave(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    url = f"/api/applicants/{applicant_id}"
    assert recruiter.get(url).json()["hired_at"] is None
    recruiter.patch(f"{url}/stage", json={"stage": "hired"})
    assert recruiter.get(url).json()["hired_at"] is not None
    recruiter.patch(f"{url}/stage", json={"stage": "offer"})
    assert recruiter.get(url).json()["hired_at"] is None

def test_summary_counts_through_api(recruiter):
    hired = apply(recruiter).json()["id"]
    refused = post_apply(recruiter, email="b@example.com", source="linkedin").json()["id"]
    recruiter.patch(f"/api/applicants/{hired}/stage", json={"stage": "hired"})
    recruiter.post(f"/api/applicants/{refused}/refuse", json={"reason": "spam"})

    rows = recruiter.get("/api/reports/summary").json()
    assert {r["job_id"] for r in rows} == {1, 2}
    [job] = recruiter.get("/api/reports/summary?job_id=1").json()
    assert job["total"] == 2 and job["hired"] == 1 and job["openings"] == 1
    assert job["by_stage"]["hired"] == 1 and job["by_stage"]["rejected"] == 1 and job["by_stage"]["new"] == 0
    assert job["by_source"] == {"careers_site": 1, "linkedin": 1, "referral": 0, "job_board": 0, "other": 0}
    assert job["refused_by_reason"]["spam"] == 1 and job["refused_by_reason"]["duplicate"] == 0
    assert job["avg_days_to_hire"] == 0.0
    assert recruiter.get("/api/reports/summary?job_id=999").status_code == 404

def test_avg_days_to_hire_only_counts_hired():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with Session(engine) as session:
        session.add(Job(id=1, title="Dev", openings=3))
        session.add_all([
            Applicant(job_id=1, name="A", email="a@x", stage=Stage.hired, created_at=start, hired_at=start + timedelta(days=10)),
            Applicant(job_id=1, name="B", email="b@x", stage=Stage.hired, created_at=start, hired_at=start + timedelta(days=5)),
            Applicant(job_id=1, name="C", email="c@x", source=Source.referral, stage=Stage.rejected,
                      refuse_reason=RefuseReason.duplicate, created_at=start),
        ])
        session.commit()
        [row] = reports.summary(session, 1)
    assert row["avg_days_to_hire"] == 7.5 and row["hired"] == 2 and row["openings"] == 3
    assert row["by_source"]["referral"] == 1 and row["refused_by_reason"]["duplicate"] == 1

def test_stage_rules_include_requirements(recruiter):
    rules = recruiter.get("/api/stage-rules").json()
    assert set(rules["requirements"]) == set(rules["stuck_after_days"])
    assert rules["requirements"]["interview"] and rules["requirements"]["hired"] == ""

def test_talent_pool_crud_and_members(recruiter):
    pool = recruiter.post("/api/talent-pools", json={"name": "Java devs", "description": "Backend"}).json()
    assert recruiter.post("/api/talent-pools", json={"name": " java DEVS "}).status_code == 409
    assert recruiter.post("/api/talent-pools", json={"name": ""}).status_code == 422
    other = recruiter.post("/api/talent-pools", json={"name": "Designers"}).json()
    assert recruiter.put(f"/api/talent-pools/{other['id']}", json={"name": "Java devs"}).status_code == 409
    assert recruiter.put(f"/api/talent-pools/{pool['id']}", json={"name": "Java", "description": ""}).json()["name"] == "Java"

    applicant_id = apply(recruiter).json()["id"]
    members_url = f"/api/talent-pools/{pool['id']}/members"
    for _ in range(2):  # adding twice is a no-op
        assert recruiter.post(members_url, json={"applicant_id": applicant_id}).status_code == 204
    assert recruiter.post(members_url, json={"applicant_id": 999}).status_code == 404
    [member] = recruiter.get(members_url).json()
    assert member["name"] == "An" and member["job_title"] == "Backend Developer"
    assert recruiter.get(f"/api/applicants/{applicant_id}/talent-pools").json() == [pool["id"]]
    counts = {p["name"]: p["member_count"] for p in recruiter.get("/api/talent-pools").json()}
    assert counts == {"Java": 1, "Designers": 0}
    activity = [a["message"] for a in recruiter.get(f"/api/applicants/{applicant_id}").json()["activity"]]
    assert activity.count("Added to talent pool: Java") == 1

    assert recruiter.delete(f"{members_url}/{applicant_id}").status_code == 204
    assert recruiter.get(members_url).json() == []
    recruiter.post(members_url, json={"applicant_id": applicant_id})
    assert recruiter.delete(f"/api/talent-pools/{pool['id']}").status_code == 204
    assert recruiter.get(members_url).status_code == 404
    assert recruiter.get(f"/api/applicants/{applicant_id}").status_code == 200  # applicant stays

def test_reports_and_pools_need_recruiter(client):
    assert client.get("/api/reports/summary").status_code == 401
    assert client.get("/api/talent-pools").status_code == 401
