"""Copy to another job, extra attachments, recruiter / to-do owners, "not interested" email."""

from app.modules.mail_templates.defaults import DEFAULTS
from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)
from tests.test_applicant_extras import add_job, detail

def add_user(recruiter, email="bob@example.com"):
    return recruiter.post("/api/admin/users", json={"email": email, "name": "Bob", "role": "recruiter",
                                                    "password": "password1"}).json()["id"]

def me(recruiter):
    return recruiter.get("/api/auth/me").json()["id"]

def test_copy_to_job_new_stage_same_cv_and_conflict(recruiter):
    source_id = apply(recruiter).json()["id"]
    recruiter.patch(f"/api/applicants/{source_id}/stage", json={"stage": "screening"})
    job_id = add_job(recruiter, "Data Engineer")

    response = recruiter.post(f"/api/applicants/{source_id}/copy", json={"job_id": job_id})
    assert response.status_code == 201
    copy = detail(recruiter, response.json()["id"])
    assert copy["job_id"] == job_id and copy["stage"] == "new" and copy["email"] == "an@example.com"
    assert copy["cv_text"] == "Java, SQL, REST APIs" and copy["source"] == "careers_site"
    assert copy["activity"][-1]["message"] == "Copied from Backend Developer"
    assert detail(recruiter, source_id)["activity"][-1]["message"] == "Copied to Data Engineer"
    assert recruiter.get(f"/api/applicants/{copy['id']}/cv").content == b"Java, SQL, REST APIs"

    assert recruiter.post(f"/api/applicants/{source_id}/copy", json={"job_id": job_id}).status_code == 409
    assert recruiter.post(f"/api/applicants/{source_id}/copy", json={"job_id": 999}).status_code == 404

def test_attachments_upload_list_download_delete(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    url = f"/api/applicants/{applicant_id}/attachments"
    response = recruiter.post(url, files={"file": ("photo.PNG", b"\x89PNG data", "text/html")})
    assert response.status_code == 201
    attachment = response.json()
    assert attachment["content_type"] == "image/png" and attachment["size"] == 9 and "stored_path" not in attachment

    listed = detail(recruiter, applicant_id)["attachments"]
    assert [a["filename"] for a in listed] == ["photo.PNG"]
    download = recruiter.get(f"{url}/{attachment['id']}")
    assert download.content == b"\x89PNG data" and download.headers["content-type"] == "image/png"

    for bad in (("x.exe", b"MZ"), ("empty.pdf", b""), ("big.pdf", b"x" * (5 * 1024 * 1024 + 1))):
        assert recruiter.post(url, files={"file": bad}).status_code == 422
    # Another applicant's id in the URL never reaches this attachment.
    other_id = apply(recruiter, email="b@example.com").json()["id"]
    assert recruiter.get(f"/api/applicants/{other_id}/attachments/{attachment['id']}").status_code == 404

    assert recruiter.delete(f"{url}/{attachment['id']}").status_code == 204
    assert detail(recruiter, applicant_id)["attachments"] == []
    assert recruiter.get(f"{url}/{attachment['id']}").status_code == 404
    assert detail(recruiter, applicant_id)["activity"][-1]["message"] == "Attachment deleted: photo.PNG"

def test_owners_patch_validate_and_board_mine_filter(recruiter):
    mine_id = apply(recruiter).json()["id"]
    other_id = apply(recruiter, email="b@example.com").json()["id"]
    bob = add_user(recruiter)
    me_id = me(recruiter)

    updated = recruiter.patch(f"/api/applicants/{mine_id}", json={"user_id": me_id, "next_action": "Call",
                                                                   "next_action_user_id": bob}).json()
    assert updated["user_id"] == me_id and updated["next_action_user_id"] == bob
    recruiter.patch(f"/api/applicants/{other_id}", json={"user_id": bob})

    mine = recruiter.get("/api/applicants", params={"job_id": 1, "owner": "me"}).json()
    assert [a["id"] for a in mine] == [mine_id]
    assert len(recruiter.get("/api/applicants", params={"job_id": 1}).json()) == 2
    assert recruiter.get("/api/applicants", params={"owner": "bob"}).status_code == 422

    recruiter.patch(f"/api/admin/users/{bob}", json={"is_active": False})
    assert recruiter.patch(f"/api/applicants/{mine_id}", json={"user_id": bob}).status_code == 422
    assert recruiter.patch(f"/api/applicants/{mine_id}", json={"next_action_user_id": 999}).status_code == 422
    assert recruiter.patch(f"/api/applicants/{mine_id}", json={"user_id": None}).json()["user_id"] is None

def test_withdrawn_reasons_send_not_interested_email(recruiter, candidate_mails):
    for email, reason, subject in (("a@example.com", "refused_salary", "Sorry to see you go: Backend Developer"),
                                   ("b@example.com", "refused_job_fit", "Sorry to see you go: Backend Developer"),
                                   ("c@example.com", "does_not_fit", "Your application for Backend Developer")):
        applicant_id = apply(recruiter, email=email).json()["id"]
        result = recruiter.post(f"/api/applicants/{applicant_id}/refuse", json={"reason": reason, "send_email": True})
        assert result.json()["emailed"] is True
        assert candidate_mails[-1] == {"to": [email], "subject": subject}
    assert DEFAULTS["not_interested"].subject != DEFAULTS["refusal"].subject
