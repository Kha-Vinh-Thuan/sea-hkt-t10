from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReportResponse:
    run_id: str
    report_status: str
    overall_status: str
    summary: str
    branch_states: tuple[dict[str, Any], ...]
    findings: tuple[dict[str, Any], ...]
    evidence_gaps: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]
    open_items: tuple[str, ...]
    next_actions: tuple[dict[str, Any], ...]
    artifact_refs: tuple[dict[str, Any], ...]

    def to_dict(self):
        return asdict(self)
