from ..dto.requests import ReportRequest
from ..dto.responses import ReportResponse


VALID_BRANCH_STATUSES = {'Complete', 'Needs input', 'Failed', 'blocked', 'cancelled', 'outdated'}


class ReportService:
    """Compile supplied handoffs without inventing evidence or decisions."""

    def execute(self, request: ReportRequest) -> ReportResponse:
        branches = tuple(self._normalize_branch(branch) for branch in request.branches)
        requested = tuple(branch for branch in branches if branch['requested'])
        missing_scope = not requested
        findings = tuple(item for branch in branches for item in branch['findings'])
        gaps = tuple(item for branch in branches for item in branch['evidence_gaps'])
        limitations = tuple(dict.fromkeys(item for branch in branches for item in branch['limitations']))
        open_items = tuple(dict.fromkeys(item for branch in branches for item in branch['open_items']))
        actions = tuple(
            {'branch': branch['name'], 'action': branch['next_action'], 'owner': 'Orchestrator'}
            for branch in branches if branch['next_action']
        )
        artifacts = tuple(item for branch in branches for item in branch['artifact_refs'])
        failed = any(branch['status'] == 'Failed' for branch in requested)
        incomplete = any(branch['status'] in {'Needs input', 'blocked', 'cancelled', 'outdated'} for branch in requested)
        overall_status = 'Failed' if failed else ('Needs input' if missing_scope or incomplete or gaps or open_items else 'Complete')
        summary = self._summary(request, branches, overall_status, len(findings), len(gaps))
        return ReportResponse(
            run_id=request.run_id,
            report_status='Complete' if not missing_scope else 'Needs input',
            overall_status=overall_status,
            summary=summary,
            branch_states=branches,
            findings=findings,
            evidence_gaps=gaps,
            limitations=limitations,
            open_items=open_items,
            next_actions=actions,
            artifact_refs=artifacts,
        )

    @staticmethod
    def _normalize_branch(branch):
        status = branch.status if branch.status in VALID_BRANCH_STATUSES else 'Needs input'
        return {
            'name': branch.name,
            'status': status,
            'requested': branch.requested,
            'summary': branch.summary,
            'findings': list(branch.findings),
            'evidence_gaps': list(branch.evidence_gaps),
            'limitations': list(branch.limitations),
            'open_items': list(branch.open_items),
            'next_action': branch.next_action,
            'artifact_refs': list(branch.artifact_refs),
        }

    @staticmethod
    def _summary(request, branches, overall_status, finding_count, gap_count):
        branch_text = ', '.join(f"{b['name']}={b['status']}" for b in branches)
        return (
            f"Report for {request.candidate_id}: overall status {overall_status}. "
            f"Branches: {branch_text}. Preserved {finding_count} finding(s) and {gap_count} evidence gap(s)."
        )
