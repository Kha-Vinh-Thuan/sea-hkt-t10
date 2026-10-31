from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BranchHandoff:
    name: str
    status: str
    requested: bool
    summary: str = ''
    findings: tuple[dict[str, Any], ...] = ()
    evidence_gaps: tuple[dict[str, Any], ...] = ()
    limitations: tuple[str, ...] = ()
    open_items: tuple[str, ...] = ()
    next_action: str = ''
    artifact_refs: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ReportRequest:
    run_id: str
    assignment: str
    candidate_id: str
    role_id: str = ''
    role_version: str = ''
    branches: tuple[BranchHandoff, ...] = ()
    model: str = ''

    def __post_init__(self):
        if not self.run_id or not self.assignment or not self.candidate_id:
            raise ValueError('run_id, assignment and candidate_id are required')
        if not self.branches:
            raise ValueError('at least one branch handoff is required')
