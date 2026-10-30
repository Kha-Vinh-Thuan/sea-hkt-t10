"""Calendar: free slots (own interviews / Google busy), propose times -> public booking, Accept / Decline,
Google event sync (failure keeps the booking), Google connect state check. Google is always monkeypatched."""

from datetime import datetime, time, timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config.database import get_session
from app.integrations import google_calendar
from app.integrations.google_calendar import GoogleError
from app.main import app
from app.modules.bookings import service as bookings_service
from app.modules.bookings.models import SlotProposal
from app.modules.google.models import GoogleCredential
from app.utils.time import utcnow
from tests.test_api import apply, client, recruiter, sent  # noqa: F401 (fixtures)

ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
MARC = "marc@example.com"

def db() -> Session:
    return next(app.dependency_overrides[get_session]())

def next_monday(hour: int, minute: int = 0) -> datetime:
    """A working-day time next week, in the app timezone (always in the future)."""
    today = datetime.now(ZONE).date()
    day = today + timedelta(days=7 - today.weekday())
    return datetime.combine(day, time(hour, minute), ZONE)

@pytest.fixture
def public(client):
    """A second browser without login: the candidate."""
    return TestClient(app)

@pytest.fixture
def marc(recruiter):
    response = recruiter.post("/api/admin/users", json={"email": MARC, "name": "Marc", "role": "interviewer",
                                                        "password": "password1"})
    return response.json()["id"]

@pytest.fixture
def google_connected(marc):
    session = db()
    session.add(GoogleCredential(user_id=marc, refresh_token="refresh-secret", email=MARC))
    session.commit()
    return marc

@pytest.fixture
def proposal_mails(monkeypatch):
    mails = []
    monkeypatch.setattr(bookings_service, "send_mail", lambda to, subject, body: mails.append({"to": to, "body": body}))
    return mails

def book(recruiter, applicant_id, start: datetime, email=MARC):
    return recruiter.post(f"/api/applicants/{applicant_id}/interviews",
                          json={"start": start.isoformat(), "interviewer_email": email})

def slot_starts(recruiter, user_id, applicant_id) -> set[datetime]:
    slots = recruiter.get(f"/api/interviewers/{user_id}/free-slots?applicant_id={applicant_id}&days=9").json()
    return {datetime.fromisoformat(s["start"]) for s in slots}

def test_free_slots_skip_own_interviews_and_weekends(recruiter, sent, marc):
    applicant_id = apply(recruiter).json()["id"]
    assert book(recruiter, applicant_id, next_monday(10)).status_code == 201

    starts = slot_starts(recruiter, marc, applicant_id)

    # 45 min interviews every 30 min: 09:30 / 10:00 / 10:30 overlap the 10:00-10:45 interview.
    assert next_monday(9) in starts and next_monday(11) in starts
    assert not {next_monday(9, 30), next_monday(10), next_monday(10, 30)} & starts
    assert next_monday(16) in starts and next_monday(16, 30) not in starts  # 16:30 + 45 min ends after 17:00
    assert all(s.astimezone(ZONE).weekday() < 5 for s in starts)

def test_free_slots_use_google_busy_when_connected(recruiter, google_connected, monkeypatch):
    calls = []
    def fake_busy(token, start, end):
        calls.append(token)
        return [(next_monday(13), next_monday(14))]
    monkeypatch.setattr(google_calendar, "busy", fake_busy)

    starts = slot_starts(recruiter, google_connected, apply(recruiter).json()["id"])

    assert calls == ["refresh-secret"]
    assert next_monday(12) in starts and next_monday(14) in starts
    assert not {next_monday(12, 30), next_monday(13), next_monday(13, 30)} & starts

def propose(recruiter, applicant_id, marc, *starts):
    return recruiter.post(f"/api/applicants/{applicant_id}/slot-proposals",
                          json={"interviewer_id": marc, "slots": [s.isoformat() for s in starts], "location": "Room 1"})

def token_of(result) -> str:
    return result["link"].rsplit("/", 1)[1]

def test_propose_then_candidate_books_through_the_interviews_service(public, recruiter, sent, marc, proposal_mails):
    applicant_id = apply(recruiter).json()["id"]
    result = propose(recruiter, applicant_id, marc, next_monday(9), next_monday(11)).json()
    assert result["emailed"] and result["link"] in proposal_mails[0]["body"]
    assert result["link"].startswith("http://localhost:5173/book/")
    token = token_of(result)
    client = public

    page = client.get(f"/api/public/bookings/{token}").json()
    assert [datetime.fromisoformat(s["start"]) for s in page["slots"]] == [next_monday(9), next_monday(11)]
    assert "interviewer" not in str(page)
    booked = client.post(f"/api/public/bookings/{token}", json={"start": next_monday(11).isoformat()})

    assert booked.status_code == 200 and booked.json()["location"] == "Room 1"
    assert len(sent) == 1 and sent[0]["to"] == ["an@example.com", MARC]
    assert client.get(f"/api/public/bookings/{token}").status_code == 409
    assert client.post(f"/api/public/bookings/{token}", json={"start": next_monday(9).isoformat()}).status_code == 409
    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert [i["status"] for i in detail["interviews"]] == ["scheduled"] and detail["stage"] == "interview"
    assert any(a["message"].startswith("Candidate booked") for a in detail["activity"])
    assert db().get(SlotProposal, result["id"]).status == "booked"

def test_taken_slot_is_hidden_and_rejected(public, recruiter, sent, marc, proposal_mails):
    token = token_of(propose(recruiter, apply(recruiter).json()["id"], marc, next_monday(9)).json())
    book(recruiter, apply(recruiter, email="binh@example.com").json()["id"], next_monday(9, 30))
    client = public

    assert client.get(f"/api/public/bookings/{token}").json()["slots"] == []
    assert client.post(f"/api/public/bookings/{token}", json={"start": next_monday(9).isoformat()}).status_code == 409
    # A time that was never proposed is refused too.
    assert client.post(f"/api/public/bookings/{token}", json={"start": next_monday(15).isoformat()}).status_code == 409

def test_expired_or_unknown_link(public, recruiter, marc, proposal_mails):
    client = public
    result = propose(recruiter, apply(recruiter).json()["id"], marc, next_monday(9)).json()
    session = db()
    proposal = session.get(SlotProposal, result["id"])
    proposal.expires_at = utcnow() - timedelta(minutes=1)  # UTC: SQLite drops the offset
    session.add(proposal)
    session.commit()

    assert client.get(f"/api/public/bookings/{token_of(result)}").status_code == 410
    assert client.post(f"/api/public/bookings/{token_of(result)}",
                       json={"start": next_monday(9).isoformat()}).status_code == 410
    assert client.get("/api/public/bookings/nope").status_code == 404
    assert propose(recruiter, apply(recruiter, email="c@example.com").json()["id"], marc,
                   datetime.now(ZONE) - timedelta(hours=1)).status_code == 422

def test_candidate_accepts_then_declines_from_the_email_links(public, recruiter, sent):
    client = public
    applicant_id = apply(recruiter).json()["id"]
    book(recruiter, applicant_id, next_monday(10))
    link = next(line for line in sent[0]["body"].splitlines() if "answer=accept" in line).split()[-1]
    token = urlparse(link).path.rsplit("/", 1)[1]

    url = f"/api/public/interviews/{token}/response"
    assert client.post(url, params={"answer": "accepted"}).json()["candidate_response"] == "accepted"
    assert client.post(url, params={"answer": "declined"}).json()["candidate_response"] == "declined"
    assert client.post(url, params={"answer": "maybe"}).status_code == 422
    assert client.get("/api/public/interviews/wrong").status_code == 404

    detail = recruiter.get(f"/api/applicants/{applicant_id}").json()
    assert detail["interviews"][0]["candidate_response"] == "declined"
    assert [a["message"][:18] for a in detail["activity"] if a["message"].startswith("Candidate ")] == [
        "Candidate accepted", "Candidate declined"]
    assert "response_token" not in recruiter.get("/api/interviews").json()[0]

def test_google_event_created_moved_deleted_and_failure_keeps_booking(recruiter, sent, google_connected, monkeypatch):
    saved, deleted = [], []
    def fake_save(token, event_id, body):
        saved.append((event_id, body))
        return "event-1", "https://meet.google.com/abc-defg-hij"
    monkeypatch.setattr(google_calendar, "save_event", fake_save)
    monkeypatch.setattr(google_calendar, "delete_event", lambda token, event_id: deleted.append(event_id))
    applicant_id = apply(recruiter).json()["id"]

    interview = book(recruiter, applicant_id, next_monday(10)).json()["interview"]
    assert (interview["google_event_id"], interview["meet_url"]) == ("event-1", "https://meet.google.com/abc-defg-hij")
    assert interview["location"] == interview["meet_url"]
    assert saved[0][0] == "" and saved[0][1]["attendees"] == [{"email": "an@example.com"}]
    assert "LOCATION:https://meet.google.com/abc-defg-hij" in sent[0]["ics"]

    recruiter.put(f"/api/interviews/{interview['id']}", json={"start": next_monday(11).isoformat(),
                                                              "interviewer_email": MARC})
    assert saved[1][0] == "event-1" and "conferenceData" not in saved[1][1]
    recruiter.post(f"/api/interviews/{interview['id']}/cancel")
    assert deleted == ["event-1"]

    def broken(*_args):
        raise GoogleError("Google returned 503", 503)
    monkeypatch.setattr(google_calendar, "save_event", broken)
    second = book(recruiter, apply(recruiter, email="binh@example.com").json()["id"], next_monday(14))
    assert second.status_code == 201 and second.json()["interview"]["google_event_id"] == ""
    messages = [a["message"] for a in recruiter.get(f"/api/applicants/{second.json()['interview']['applicant_id']}")
                .json()["activity"]]
    assert "Google Calendar not updated: Google returned 503" in messages and "Invitation emailed" in messages

def test_google_connect_state_is_signed_and_checked(public, recruiter, monkeypatch):
    client = public
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(google_calendar, "exchange_code", lambda code: ("refresh-new", "hr@gmail.com"))
    url = recruiter.get("/api/google/connect").json()["url"]
    query = parse_qs(urlparse(url).query)
    assert query["access_type"] == ["offline"] and query["prompt"] == ["consent"]
    assert "calendar.freebusy" in query["scope"][0] and "calendar.events" in query["scope"][0]
    state = query["state"][0]
    user_id, expires, signature = state.split(".")

    for bad in (f"{int(user_id) + 1}.{expires}.{signature}", f"{user_id}.{int(expires) + 60}.{signature}", "", "x"):
        assert client.get("/api/google/callback", params={"state": bad, "code": "c"},
                          follow_redirects=False).status_code == 422
    assert recruiter.get("/api/auth/me").json()["google_connected"] is False

    done = client.get("/api/google/callback", params={"state": state, "code": "c"}, follow_redirects=False)
    assert done.status_code == 303 and done.headers["location"].endswith("/?google=connected")
    assert recruiter.get("/api/auth/me").json()["google_connected"] is True

    monkeypatch.setattr(google_calendar, "revoke", lambda token: None)
    assert recruiter.delete("/api/google/connection").status_code == 204
    assert recruiter.get("/api/auth/me").json()["google_connected"] is False

def test_booking_rechecks_google_live_even_after_a_cached_view(recruiter, sent, google_connected, monkeypatch):
    applicant_id = apply(recruiter).json()["id"]
    meeting = [(next_monday(14), next_monday(15))]
    calendar = []  # Google is empty when the recruiter looks, the techlead adds a meeting afterwards
    monkeypatch.setattr(google_calendar, "busy", lambda token, start, end: list(calendar))
    monkeypatch.setattr(google_calendar, "save_event", lambda token, event_id, body: ("evt", ""))

    view = recruiter.get("/api/interviewers/busy", params={"user_ids": [google_connected],
                                                            "start": next_monday(0).isoformat()}).json()
    assert view[0]["busy"] == [] and view[0]["google_ok"]
    calendar.extend(meeting)

    response = book(recruiter, applicant_id, next_monday(14, 30))
    assert response.status_code == 409 and "Google Calendar" in response.json()["detail"]
    assert book(recruiter, applicant_id, next_monday(16)).status_code == 201

def test_booking_goes_ahead_with_a_warning_when_google_is_down(recruiter, sent, google_connected, monkeypatch):
    applicant_id = apply(recruiter).json()["id"]
    def down(token, start, end):
        raise GoogleError("503")
    monkeypatch.setattr(google_calendar, "busy", down)
    monkeypatch.setattr(google_calendar, "save_event", lambda token, event_id, body: ("evt", ""))

    assert book(recruiter, applicant_id, next_monday(10)).status_code == 201
    activity = [a["message"] for a in recruiter.get(f"/api/applicants/{applicant_id}").json()["activity"]]
    assert "Could not check Google Calendar, booked without it" in activity

def test_team_calendar_shows_busy_blocks_of_several_interviewers(recruiter, sent, google_connected, monkeypatch):
    other = recruiter.post("/api/admin/users", json={"email": "lan@example.com", "name": "Lan", "role": "interviewer",
                                                     "password": "password1"}).json()["id"]
    applicant_id = apply(recruiter).json()["id"]
    monkeypatch.setattr(google_calendar, "busy", lambda token, start, end: [(next_monday(9), next_monday(10))])
    monkeypatch.setattr(google_calendar, "save_event", lambda token, event_id, body: ("evt", ""))
    assert book(recruiter, applicant_id, next_monday(11), email="lan@example.com").status_code == 201

    rows = recruiter.get("/api/interviewers/busy", params={"user_ids": [google_connected, other],
                                                            "start": next_monday(0).isoformat(), "days": 5}).json()
    by_name = {r["name"]: r for r in rows}
    assert by_name["Marc"]["google_connected"] and [b["source"] for b in by_name["Marc"]["busy"]] == ["google"]
    assert not by_name["Lan"]["google_connected"] and [b["source"] for b in by_name["Lan"]["busy"]] == ["interview"]
    assert "summary" not in str(rows)  # only times, never event titles

def test_google_busy_is_cached_for_views(recruiter, google_connected, monkeypatch):
    calls = []
    monkeypatch.setattr(google_calendar, "busy", lambda token, start, end: calls.append(1) or [])
    params = {"user_ids": [google_connected], "start": next_monday(0).isoformat()}
    recruiter.get("/api/interviewers/busy", params=params)
    recruiter.get("/api/interviewers/busy", params=params)
    assert len(calls) == 1
