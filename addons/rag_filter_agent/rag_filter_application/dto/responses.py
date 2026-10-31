from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceRef:
    document_id: str
    source_hash: str
    quote: str
    page: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    provenance: str = 'candidate_self_report'


@dataclass(frozen=True)
class FindingResponse:
    criterion_id: str
    status: str
    finding: str
    evidence: tuple[EvidenceRef, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceGapResponse:
    criterion_id: str
    reason: str
    question_intent: str
    priority: str = 'normal'


@dataclass(frozen=True)
class FilterHandoff:
    run_id: str
    candidate_id: str
    role_id: str
    role_version: str
    status: str
    summary: str
    findings: tuple[FindingResponse, ...]
    evidence_gaps: tuple[EvidenceGapResponse, ...]
    limitations: tuple[str, ...]
    open_items: tuple[str, ...]
    next_action: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class RequirementResponse:
    name: str
    priority: str


@dataclass(frozen=True)
class CandidateResultResponse:
    rank: int
    filename: str
    candidate: str
    score: int
    summary: str
    items: tuple[dict[str, Any], ...]
    error: str = ''


@dataclass(frozen=True)
class ScreeningResponse:
    job: str
    requirements: tuple[RequirementResponse, ...]
    results: tuple[CandidateResultResponse, ...]

    def to_dict(self):
        return asdict(self)
