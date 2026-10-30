"""Recruiter actions on one applicant through HTTP: edit fields, refuse with reason + email, archive / restore,
and the candidate emails (interest on apply, congratulations on hire).
"""

from app.modules.applicants import emails
from app.integrations.mail import MailError
from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)


def fail_mail(*_args, **_kw):
    raise MailError("Could not send email: connection refused")


def messages(recruiter, applicant_id):
    return [a["message"] for a in recruiter.get(f"/api/applicants/{applicant_id}").json()["activity"]]


def test_apply_sends_interest_email_and_accepts_linkedin_intro(recruiter, candidate_mails):
    response = recruiter.post("/api/public/jobs/1/apply", files={"cv": ("cv.txt", b"Java")}, data={
        "name": "An", "email": "an@example.com", "linkedin": "https://linkedin.com/in/an", "short_intro": "Hi"})
    applicant_id = response.json()["id"]
    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert detail["linkedin"] == "https://linkedin.com/in/an" and detail["short_intro"] == "Hi"
    assert candidate_mails == [{"to": ["an@example.com"], "subject": "We received your application for Backend Developer"}]
    assert messages(recruiter, applicant_id)[-1] == "Interest email sent"

    bad = {"name": "B", "email": "b@example.com"}
    assert recruiter.post("/api/public/jobs/1/apply", files={"cv": ("cv.txt", b"x")},
                          data={**bad, "linkedin": "javascript:alert(1)"}).status_code == 422
    assert recruiter.post("/api/public/jobs/1/apply", files={"cv": ("cv.txt", b"x")},
                          data={**bad, "short_intro": "x" * 2001}).status_code == 422


def test_interest_mail_failure_does_not_break_apply(recruiter, monkeypatch):
    monkeypatch.setattr(emails, "send_mail", fail_mail)
    response = apply(recruiter)
    assert response.status_code == 201
    assert messages(recruiter, response.json()["id"])[-1] == "Email not sent: Could not send email: connection refused"


def test_patch_updates_fields_logs_names_and_validates(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    url = f"/api/applicants/{applicant_id}"
    body = {"notes": "secret remark", "priority": 3, "tags": ["java", "java", " senior "], "salary_expected": 1000}
    updated = recruiter.patch(url, json=body).json()
    assert updated["priority"] == 3 and updated["tags"] == ["java", "senior"] and updated["degree"] == ""
    assert messages(recruiter, applicant_id)[-1] == "Updated: notes, priority, tags, salary_expected"

    for bad in ({"priority": 4}, {"salary_proposed": -1}, {"linkedin": "linkedin.com/in/x"}):
        assert recruiter.patch(url, json=bad).status_code == 422


def test_plain_stage_patch_to_rejected_is_refused(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    response = recruiter.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "rejected"})
    assert response.status_code == 422 and "refuse" in response.json()["detail"]


def test_refuse_records_reason_and_emails(recruiter, candidate_mails):
    applicant_id = apply(recruiter).json()["id"]
    result = recruiter.post(f"/api/applicants/{applicant_id}/refuse",
                            json={"reason": "refused_salary", "send_email": True}).json()
    assert result["emailed"] is True and result["mail_error"] is None
    assert result["applicant"]["stage"] == "rejected" and result["applicant"]["refuse_reason"] == "refused_salary"
    assert result["applicant"]["refused_at"]
    # Withdrawn by the applicant (salary): the "not interested" template, see test_applicant_more.py.
    assert candidate_mails[-1]["subject"] == "Sorry to see you go: Backend Developer"
    assert recruiter.post(f"/api/applicants/{applicant_id}/refuse", json={"reason": "bogus"}).status_code == 422


def test_refuse_mail_failure_keeps_the_refusal(recruiter, monkeypatch):
    applicant_id = apply(recruiter).json()["id"]
    monkeypatch.setattr(emails, "send_mail", fail_mail)
    result = recruiter.post(f"/api/applicants/{applicant_id}/refuse",
                            json={"reason": "does_not_fit", "send_email": True}).json()
    assert result["emailed"] is False and "connection refused" in result["mail_error"]
    assert recruiter.get(f"/api/applicants/{applicant_id}").json()["stage"] == "rejected"


def test_archive_hides_from_board_and_restore_resets(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    recruiter.post(f"/api/applicants/{applicant_id}/refuse", json={"reason": "spam"})
    recruiter.post(f"/api/applicants/{applicant_id}/archive")
    assert recruiter.get("/api/applicants", params={"job_id": 1}).json() == []
    assert [a["id"] for a in recruiter.get("/api/applicants", params={"archived": True}).json()] == [applicant_id]

    restored = recruiter.post(f"/api/applicants/{applicant_id}/restore").json()
    assert restored["archived"] is False and restored["stage"] == "new"
    assert restored["refuse_reason"] is None and restored["refused_at"] is None
    assert [a["id"] for a in recruiter.get("/api/applicants").json()] == [applicant_id]


def test_moving_to_hired_sends_congratulations_once(recruiter, candidate_mails):
    applicant_id = apply(recruiter).json()["id"]
    before = recruiter.get(f"/api/applicants/{applicant_id}").json()["stage_changed_at"]
    recruiter.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "hired"})
    recruiter.patch(f"/api/applicants/{applicant_id}/stage", json={"stage": "hired"})
    assert [m["subject"] for m in candidate_mails][1:] == ["Congratulations! Welcome aboard as Backend Developer"]
    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert detail["stage_changed_at"] > before
    assert detail["activity"][-1]["message"] == "Congratulations email sent"
