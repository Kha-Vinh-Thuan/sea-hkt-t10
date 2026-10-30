"""Mail templates + composer: safe rendering, seeded defaults, admin-only CRUD, compose / send with activity log."""

from app.integrations.mail import MailError
from app.modules.applicants import emails
from app.modules.mail_templates.service import render
from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)
from tests.test_users import add_user, token_for

def templates(client, **kw):
    return {t["key"]: t for t in client.get("/api/mail-templates", **kw).json()}

def last_activity(recruiter, applicant_id):
    return recruiter.get(f"/api/applicants/{applicant_id}").json()["activity"][-1]["message"]

def test_render_fills_known_and_keeps_unknown_placeholders():
    values = {"name": "An", "job": "Dev"}
    assert render("Hi {name}, {job}!", values) == "Hi An, Dev!"
    # Unknown, attribute access, positional and lone braces all stay as typed and never raise.
    text = "{unknown} {name.__class__} {0} { } {"
    assert render(text, values) == text

def test_defaults_seeded_with_stages(recruiter, monkeypatch):
    monkeypatch.setenv("COMPANY_NAME", "Acme")
    by_key = templates(recruiter)
    assert set(by_key) == {"interest", "refusal", "not_interested", "congratulations", "screening", "offer"}
    assert by_key["screening"]["stage"] == "screening" and by_key["offer"]["stage"] == "offer"
    assert by_key["interest"]["stage"] is None

def test_compose_renders_and_send_logs_activity(recruiter, candidate_mails, monkeypatch):
    monkeypatch.setenv("COMPANY_NAME", "Acme")
    applicant_id = apply(recruiter).json()["id"]
    offer = templates(recruiter)["offer"]
    draft = recruiter.get(f"/api/applicants/{applicant_id}/compose?template_id={offer['id']}").json()
    assert draft["subject"] == "Job offer: Backend Developer at Acme"
    assert draft["body"].startswith("Hello An,")

    result = recruiter.post(f"/api/applicants/{applicant_id}/emails", json={"subject": "Hi {name}", "body": "Body"})
    assert result.json() == {"sent": True, "error": None}
    # What the recruiter typed is final: not rendered a second time.
    assert candidate_mails[-1] == {"to": ["an@example.com"], "subject": "Hi {name}"}
    assert last_activity(recruiter, applicant_id) == "Email sent: Hi {name}\n\nBody"
    assert recruiter.get(f"/api/applicants/{applicant_id}/compose?template_id=999").status_code == 404

def test_send_failure_returns_error_and_logs(recruiter, monkeypatch):
    applicant_id = apply(recruiter).json()["id"]

    def fail(*_args, **_kw):
        raise MailError("Could not send email: connection refused")
    monkeypatch.setattr(emails, "send_mail", fail)
    response = recruiter.post(f"/api/applicants/{applicant_id}/emails", json={"subject": "S", "body": "B"})
    assert response.status_code == 200
    assert response.json() == {"sent": False, "error": "Could not send email: connection refused"}
    assert last_activity(recruiter, applicant_id) == "Email not sent: S: Could not send email: connection refused"

def test_crud_is_admin_only(recruiter):
    add_user(recruiter, "rec@example.com", "recruiter")
    headers = token_for(recruiter, "rec@example.com")
    body = {"name": "Custom", "subject": "Hello {name}", "body": "x", "stage": "interview"}
    assert recruiter.post("/api/admin/mail-templates", headers=headers, json=body).status_code == 403
    assert recruiter.get("/api/admin/mail-templates", headers=headers).status_code == 403
    assert len(templates(recruiter, headers=headers)) == 6  # recruiters can read for the composer

    created = recruiter.post("/api/admin/mail-templates", json=body)
    assert created.status_code == 201 and created.json()["key"] is None
    template_id = created.json()["id"]
    assert len(recruiter.get("/api/admin/mail-templates").json()) == 7  # defaults seeded before the custom one
    updated = recruiter.put(f"/api/admin/mail-templates/{template_id}", json={**body, "stage": None}).json()
    assert updated["stage"] is None
    assert recruiter.delete(f"/api/admin/mail-templates/{template_id}").status_code == 204
    assert recruiter.delete(f"/api/admin/mail-templates/{template_id}").status_code == 404

def test_automatic_emails_use_edited_template_and_fall_back(recruiter, candidate_mails):
    interest = templates(recruiter)["interest"]
    recruiter.put(f"/api/admin/mail-templates/{interest['id']}",
                  json={"name": interest["name"], "subject": "Thanks {name} for {job}", "body": "b"})
    apply(recruiter)
    assert candidate_mails[-1]["subject"] == "Thanks An for Backend Developer"

    # Deleted keyed template: the code default still goes out.
    recruiter.delete(f"/api/admin/mail-templates/{interest['id']}")
    apply(recruiter, email="b@example.com")
    assert candidate_mails[-1]["subject"] == "We received your application for Backend Developer"
