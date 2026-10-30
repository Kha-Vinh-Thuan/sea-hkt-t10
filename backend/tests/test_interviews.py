"""Reschedule / cancel (.ics with the same UID, bumped SEQUENCE) and feedback rules."""

from datetime import timedelta

from sqlmodel import Session

from app.modules.interviews.models import Interview
from app.utils.time import utcnow
from tests.test_api import apply, client, recruiter, sent, tomorrow_at  # noqa: F401 (fixtures)

def book(recruiter, applicant_id, hour=3, email="marc@example.com"):
    body = {"start": tomorrow_at(hour), "interviewer_email": email}
    return recruiter.post(f"/api/applicants/{applicant_id}/interviews", json=body)

def uid(ics: str) -> str:
    return next(line for line in ics.splitlines() if line.startswith("UID:"))

def test_reschedule_moves_times_bumps_sequence_and_resends_same_uid(recruiter, sent):
    interview_id = book(recruiter, apply(recruiter).json()["id"]).json()["interview"]["id"]

    # Overlapping its own old slot is fine: the clash check ignores the interview being moved.
    result = recruiter.put(f"/api/interviews/{interview_id}",
                           json={"start": tomorrow_at(3).replace("T03:00", "T03:30"),
                                 "interviewer_email": "marc@example.com", "location": "Room 2"}).json()

    assert result["emailed"] is True
    assert result["interview"]["sequence"] == 1 and result["interview"]["location"] == "Room 2"
    assert "T03:30" in result["interview"]["start"]
    assert uid(sent[1]["ics"]) == uid(sent[0]["ics"])
    assert "METHOD:REQUEST" in sent[1]["ics"] and "SEQUENCE:1" in sent[1]["ics"]

def test_reschedule_still_rejects_clash_with_another_interview(recruiter, sent):
    first = book(recruiter, apply(recruiter).json()["id"], hour=3).json()["interview"]["id"]
    book(recruiter, apply(recruiter, email="binh@example.com").json()["id"], hour=5)
    clash = {"start": tomorrow_at(5), "interviewer_email": "marc@example.com"}
    assert recruiter.put(f"/api/interviews/{first}", json=clash).status_code == 409

def test_cancel_sends_cancel_ics_and_frees_the_slot(recruiter, sent):
    first = apply(recruiter).json()["id"]
    interview_id = book(recruiter, first).json()["interview"]["id"]

    result = recruiter.post(f"/api/interviews/{interview_id}/cancel").json()

    assert result["interview"]["status"] == "cancelled" and result["emailed"] is True
    assert "METHOD:CANCEL" in sent[1]["ics"] and "STATUS:CANCELLED" in sent[1]["ics"]
    assert sent[1]["method"] == "CANCEL" and uid(sent[1]["ics"]) == uid(sent[0]["ics"])
    assert recruiter.get("/api/interviews").json() == []
    assert book(recruiter, apply(recruiter, email="binh@example.com").json()["id"]).status_code == 201
    assert recruiter.post(f"/api/interviews/{interview_id}/cancel").status_code == 409
    assert recruiter.get(f"/api/applicants/{first}").json()["activity"][-1]["message"] == "Cancellation emailed"

def test_feedback_only_after_start_and_needs_score_when_done(recruiter, sent):
    applicant_id = apply(recruiter).json()["id"]
    future_id = book(recruiter, applicant_id).json()["interview"]["id"]
    done = {"status": "done", "score": 4, "recommendation": "hire", "feedback": "Strong SQL"}
    assert recruiter.post(f"/api/interviews/{future_id}/feedback", json=done).status_code == 422

    # Booking refuses past times, so put a finished interview straight into the DB.
    from app.config.database import get_session
    from app.main import app
    session: Session = next(app.dependency_overrides[get_session]())
    start = utcnow() - timedelta(hours=2)
    past = Interview(applicant_id=applicant_id, interviewer_email="marc@example.com", start=start,
                     end=start + timedelta(minutes=45))
    session.add(past)
    session.commit()
    url = f"/api/interviews/{past.id}/feedback"

    assert recruiter.post(url, json={"status": "done", "feedback": "x"}).status_code == 422
    assert recruiter.post(url, json={**done, "status": "cancelled"}).status_code == 422
    saved = recruiter.post(url, json=done).json()
    assert (saved["status"], saved["score"], saved["recommendation"]) == ("done", 4, "hire")
    assert recruiter.post(url, json={"status": "no_show"}).json()["status"] == "no_show"
