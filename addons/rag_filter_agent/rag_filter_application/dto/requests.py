from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentRequest:
    document_id: str
    filename: str
    content: bytes
    source_hash: str = ''


@dataclass(frozen=True)
class CriterionRequest:
    criterion_id: str
    label: str
    description: str
    required: bool = False


@dataclass(frozen=True)
class FilterRequest:
    run_id: str
    candidate_id: str
    role_id: str
    role_version: str
    criteria: tuple[CriterionRequest, ...]
    documents: tuple[DocumentRequest, ...]
    model: str

    def __post_init__(self):
        if not self.run_id or not self.candidate_id or not self.role_id or not self.role_version:
            raise ValueError('run_id, candidate_id, role_id and role_version are required')
        if not self.criteria:
            raise ValueError('at least one approved criterion is required')
        if not self.documents:
            raise ValueError('at least one candidate document is required')
        if not self.model:
            raise ValueError('model is required')


@dataclass(frozen=True)
class CandidateDocumentRequest:
    filename: str
    content: bytes


@dataclass(frozen=True)
class ScreeningRequest:
    jd_filename: str
    jd_content: bytes
    candidates: tuple[CandidateDocumentRequest, ...]
    model: str

    def __post_init__(self):
        if not self.jd_content:
            raise ValueError('JD content is required')
        if not self.candidates:
            raise ValueError('at least one candidate CV is required')
        if not self.model:
            raise ValueError('model is required')
