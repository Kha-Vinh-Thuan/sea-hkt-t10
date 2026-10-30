"""Service layer tested directly, no HTTP: the rules hold no matter which route (or agent) calls them."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Job, Stage
from app.services import applicants
from app.services.errors import Conflict, Invalid, NotFound


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Job(id=1, title="Backend Developer"))
        s.add(Job(id=2, title="Closed", is_open=False))
        s.commit()
        yield s


def test_apply_logs_activity_and_rejects_duplicates_and_closed_jobs(session):
    applicant = applicants.apply(session, 1, " An ", "an@example.com", "", "cv.txt", b"Java")
    assert applicant.name == "An" and applicant.cv_text == "Java"
    assert [a.message for a in applicants.detail(session, applicant.id)["activity"]] == ["Applied through the careers site"]

    with pytest.raises(Conflict):
        applicants.apply(session, 1, "An", "an@example.com", "", "cv.txt", b"Java")
    with pytest.raises(NotFound):
        applicants.apply(session, 2, "Binh", "binh@example.com", "", "cv.txt", b"Java")
    with pytest.raises(Invalid):
        applicants.apply(session, 1, "Chi", "chi@example.com", "", "cv.exe", b"MZ")


def test_moving_to_the_same_stage_writes_no_log(session):
    applicant = applicants.apply(session, 1, "An", "an@example.com", "", "cv.txt", b"Java")
    applicants.move_stage(session, applicant.id, Stage.new)
    applicants.move_stage(session, applicant.id, Stage.screening)
    messages = [a.message for a in applicants.detail(session, applicant.id)["activity"]]
    assert messages == ["Applied through the careers site", "Stage: new → screening"]
