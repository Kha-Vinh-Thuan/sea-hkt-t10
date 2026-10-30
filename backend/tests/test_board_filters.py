"""Board list filters (search, min priority, tag, archived) and the refuse-reason list the UI reads."""

from tests.test_api import apply, client, recruiter  # noqa: F401  (fixtures reused)


def ids(recruiter, **params):
    return sorted(a["id"] for a in recruiter.get("/api/applicants", params={"job_id": 1, **params}).json())


def test_search_priority_and_tag_filters(recruiter):
    an = apply(recruiter, email="an@example.com", file=("cv.txt", b"Kotlin and Postgres")).json()["id"]
    binh = apply(recruiter, email="binh@example.com", file=("cv.txt", b"Python")).json()["id"]
    recruiter.patch(f"/api/applicants/{an}", json={"priority": 3, "tags": ["Senior"]})
    recruiter.patch(f"/api/applicants/{binh}", json={"priority": 1, "tags": ["seniority-unknown", "100%_remote"]})

    assert ids(recruiter, q="BINH@") == [binh]               # email, case-insensitive
    assert ids(recruiter, q="postgres") == [an]              # CV text
    assert ids(recruiter, q="senior") == [an, binh]          # tag substring
    assert ids(recruiter, q="an") == [an, binh]              # name "An" on both
    assert ids(recruiter, q="0%_") == [binh]                 # LIKE wildcards are literal
    assert ids(recruiter, priority_min=2) == [an]
    assert ids(recruiter, tag="senior") == [an]              # whole tag only
    assert ids(recruiter, q="python", priority_min=2) == []  # filters combine
    assert recruiter.get("/api/applicants", params={"priority_min": 4}).status_code == 422


def test_archived_listing_is_filtered_too(recruiter):
    an = apply(recruiter, email="an@example.com").json()["id"]
    apply(recruiter, email="binh@example.com")
    recruiter.post(f"/api/applicants/{an}/archive")
    assert ids(recruiter, archived=True) == [an]
    assert ids(recruiter, archived=True, q="binh") == []


def test_refuse_reasons_have_value_and_label(recruiter):
    reasons = recruiter.get("/api/refuse-reasons").json()
    assert reasons[0] == {"value": "does_not_fit", "label": "Does not fit the job requirements"}
    assert all(r["label"] for r in reasons) and len(reasons) == 6
