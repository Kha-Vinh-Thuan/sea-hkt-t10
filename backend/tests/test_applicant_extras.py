"""Source, "also applied to", next step and stage rules (Odoo UTM / application_count / mail.activity / rotting)."""

from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)

def post_apply(client, email="an@example.com", phone="", job_id=1, **extra):
    return client.post(f"/api/public/jobs/{job_id}/apply", files={"cv": ("cv.txt", b"Java")},
                       data={"name": "An", "email": email, "phone": phone, **extra})

def detail(recruiter, applicant_id):
    return recruiter.get(f"/api/applicants/{applicant_id}").json()

def add_job(recruiter, title):
    return recruiter.post("/api/jobs", json={"title": title}).json()["id"]

def test_apply_records_source_and_rejects_unknown(recruiter):
    assert detail(recruiter, apply(recruiter).json()["id"])["source"] == "careers_site"
    applicant_id = post_apply(recruiter, email="b@example.com", source="linkedin").json()["id"]
    assert detail(recruiter, applicant_id)["source"] == "linkedin"
    assert post_apply(recruiter, email="c@example.com", source="tiktok").status_code == 422

def test_other_applications_match_email_any_case_or_phone_not_self(recruiter):
    job_a, job_b = add_job(recruiter, "Job A"), add_job(recruiter, "Job B")
    first = post_apply(recruiter, email="an@example.com", phone="0901").json()["id"]
    by_email = post_apply(recruiter, email="AN@Example.com", job_id=job_a).json()["id"]
    by_phone = post_apply(recruiter, email="other@example.com", phone="0901", job_id=job_b).json()["id"]
    stranger = post_apply(recruiter, email="x@example.com").json()["id"]

    others = detail(recruiter, first)["other_applications"]
    assert {o["id"] for o in others} == {by_email, by_phone}
    assert {o["job_title"] for o in others} == {"Job A", "Job B"} and others[0]["stage"] == "new"
    # Empty phone never matches other empty phones.
    assert detail(recruiter, stranger)["other_applications"] == []

def test_next_action_patch_logs_and_validates(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    url = f"/api/applicants/{applicant_id}"
    body = {"next_action": "Call about salary", "next_action_due": "2026-11-02", "source": "referral",
            "source_detail": "Binh"}
    updated = recruiter.patch(url, json=body).json()
    assert updated["next_action_due"] == "2026-11-02" and updated["source_detail"] == "Binh"
    assert detail(recruiter, applicant_id)["activity"][-1]["message"] == \
        "Updated: source, source_detail, next_action, next_action_due"
    for bad in ({"next_action_due": "soon"}, {"next_action": "x" * 501}, {"source": "tiktok"}):
        assert recruiter.patch(url, json=bad).status_code == 422

def test_stage_rules_shape(recruiter):
    rules = recruiter.get("/api/stage-rules").json()["stuck_after_days"]
    assert set(rules) == set(recruiter.get("/api/stages").json())
    assert rules["new"] == 3 and rules["hired"] is None and rules["rejected"] is None
