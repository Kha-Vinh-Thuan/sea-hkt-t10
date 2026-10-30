"""Shared test setup: candidate emails (interest, congratulations, refusal) never leave the test run."""

import pytest

from app.modules.applicants import emails


@pytest.fixture(autouse=True)
def candidate_mails(monkeypatch):
    # Every apply now sends a confirmation; capture instead of opening SMTP connections.
    mails = []
    monkeypatch.setattr(emails, "send_mail", lambda to, subject, body: mails.append({"to": to, "subject": subject}))
    return mails
