"""CV and attachment bytes live in stored_file (shared hosted DB), plus the one-off move from uploads/."""

from sqlmodel import Session, select

from app.config.settings import database_url
from app.modules.applicants.models import Applicant, ApplicantAttachment
from app.modules.files.models import StoredFile
from app.move_uploads_to_db import move
from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)
from tests.test_applicant_extras import add_job

def db(recruiter) -> Session:
    """A session on the test client's in-memory DB."""
    from app.config.database import get_session
    from app.main import app
    return next(app.dependency_overrides[get_session]())

def test_apply_stores_cv_bytes_in_db_and_download_returns_them(recruiter, tmp_path):
    applicant_id = apply(recruiter).json()["id"]
    with db(recruiter) as session:
        key = session.get(Applicant, applicant_id).cv_path
        stored = session.get(StoredFile, key)
        assert stored.data == b"Java, SQL, REST APIs" and stored.size == 20 and stored.content_type == "text/plain"
    assert list(tmp_path.iterdir()) == []  # nothing written to UPLOAD_DIR any more

    download = recruiter.get(f"/api/applicants/{applicant_id}/cv")
    assert download.content == b"Java, SQL, REST APIs"
    assert download.headers["content-disposition"] == 'attachment; filename="cv.txt"'

def test_copy_to_job_shares_the_same_file_row(recruiter):
    source_id = apply(recruiter).json()["id"]
    copy_id = recruiter.post(f"/api/applicants/{source_id}/copy", json={"job_id": add_job(recruiter, "QA")}).json()["id"]
    with db(recruiter) as session:
        assert session.get(Applicant, copy_id).cv_path == session.get(Applicant, source_id).cv_path
        assert len(session.exec(select(StoredFile)).all()) == 1

def test_attachment_round_trip_and_delete_removes_bytes(recruiter):
    applicant_id = apply(recruiter).json()["id"]
    url = f"/api/applicants/{applicant_id}/attachments"
    attachment_id = recruiter.post(url, files={"file": ("Bằng cấp.pdf", b"%PDF-1 data", "text/html")}).json()["id"]
    download = recruiter.get(f"{url}/{attachment_id}")
    assert download.content == b"%PDF-1 data" and download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment; filename*=utf-8''")

    assert recruiter.delete(f"{url}/{attachment_id}").status_code == 204
    with db(recruiter) as session:
        assert len(session.exec(select(StoredFile)).all()) == 1  # only the CV is left

def test_move_uploads_to_db_is_idempotent_and_keeps_files(recruiter, tmp_path):
    applicant_id = apply(recruiter).json()["id"]
    uploads = tmp_path / "old_uploads"
    uploads.mkdir()
    (uploads / "aaa.pdf").write_bytes(b"old cv")
    (uploads / "bbb.png").write_bytes(b"old photo")
    with db(recruiter) as session:
        # Rows as the disk-based version left them: disk names in cv_path / stored_path, no stored_file row.
        old = session.get(Applicant, applicant_id)
        old.cv_path, old.cv_filename = "aaa.pdf", "An CV.pdf"
        session.add(ApplicantAttachment(applicant_id=applicant_id, filename="photo.png", stored_path="bbb.png",
                                        content_type="image/png", size=9))
        session.add(ApplicantAttachment(applicant_id=applicant_id, filename="lost.pdf", stored_path="ccc.pdf",
                                        content_type="application/pdf", size=1))
        session.commit()

        assert move(session, uploads) == {"moved": 2, "already_in_db": 0, "missing_on_disk": 1}
        assert move(session, uploads) == {"moved": 0, "already_in_db": 2, "missing_on_disk": 1}
        assert session.get(StoredFile, "aaa.pdf").filename == "An CV.pdf"
    assert (uploads / "aaa.pdf").exists() and (uploads / "bbb.png").exists()
    assert recruiter.get(f"/api/applicants/{applicant_id}/cv").content == b"old cv"

def test_hosted_postgres_url_uses_psycopg_and_keeps_sslmode(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@ep-x.neon.tech/hr?sslmode=require")
    assert database_url() == "postgresql+psycopg://u:p@ep-x.neon.tech/hr?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.supabase.co:5432/postgres")
    assert database_url() == "postgresql+psycopg://u:p@db.supabase.co:5432/postgres"
