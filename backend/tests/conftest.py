"""Shared test setup: candidate emails (interest, congratulations, refusal) never leave the test run."""

import pytest

from app.modules.applicants import emails
from app.modules.auth import service as auth_service


@pytest.fixture(autouse=True)
def candidate_mails(monkeypatch):
    # Every apply now sends a confirmation; capture instead of opening SMTP connections.
    mails = []
    monkeypatch.setattr(emails, "send_mail", lambda to, subject, body: mails.append({"to": to, "subject": subject}))
    return mails

@pytest.fixture(autouse=True)
def reset_login_limit():
    # The failed-login counter is process memory; one test's wrong passwords must not lock out the next.
    auth_service._failed_logins.clear()
