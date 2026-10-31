from ..dto.requests import FilterRequest, ScreeningRequest
from ..dto.responses import (
    CandidateResultResponse,
    RequirementResponse,
    ScreeningResponse,
)
from ..dto.responses import EvidenceGapResponse, EvidenceRef, FilterHandoff, FindingResponse


class FilterService:
    """Evidence-review use case used by the SaaS orchestrator contract."""

    def __init__(self, reviewer):
        self._reviewer = reviewer

    def execute(self, request: FilterRequest) -> FilterHandoff:
        findings = []
        for document in request.documents:
            raw_findings = self._reviewer(
                request.model,
                [
                    {
                        'criterion_id': criterion.criterion_id,
                        'label': criterion.label,
                        'description': criterion.description,
                        'required': criterion.required,
                    }
                    for criterion in request.criteria
                ],
                document.filename,
                document.content,
            )
            findings.extend(self._finding(item, document) for item in raw_findings)

        # A criterion must have one aggregate finding. If multiple documents
        # exist, retain all evidence and surface disagreements as conflicts.
        by_criterion = {}
        for finding in findings:
            current = by_criterion.get(finding.criterion_id)
            if current is None:
                by_criterion[finding.criterion_id] = finding
            elif current.status != finding.status:
                by_criterion[finding.criterion_id] = FindingResponse(
                    finding.criterion_id, 'conflicting',
                    f'{current.finding} Conflicting document evidence was also found.',
                    current.evidence + finding.evidence,
                    current.limitations + finding.limitations + ('Evidence requires human clarification.',),
                )
            else:
                by_criterion[finding.criterion_id] = FindingResponse(
                    finding.criterion_id, finding.status, finding.finding,
                    current.evidence + finding.evidence,
                    current.limitations + finding.limitations,
                )

        final_findings = tuple(by_criterion.get(c.criterion_id, FindingResponse(
            c.criterion_id, 'unknown', 'No evidence was found.', (), ('No supporting evidence was provided.',)
        )) for c in request.criteria)
        gaps = tuple(EvidenceGapResponse(
            f.criterion_id,
            'No conclusive evidence was found.' if f.status == 'unknown' else 'Evidence is incomplete or conflicting.',
            f'Clarify the candidate evidence for criterion {f.criterion_id} and their personal contribution.',
            'high' if f.status == 'conflicting' else 'normal',
        ) for f in final_findings if f.status in ('unknown', 'partially_supported', 'conflicting'))
        limitations = tuple(dict.fromkeys(limit for f in final_findings for limit in f.limitations))
        return FilterHandoff(
            run_id=request.run_id,
            candidate_id=request.candidate_id,
            role_id=request.role_id,
            role_version=request.role_version,
            status='Complete' if not limitations else 'Complete',
            summary=f'Evidence review completed for {len(final_findings)} approved criteria.',
            findings=final_findings,
            evidence_gaps=gaps,
            limitations=limitations,
            open_items=tuple(g.reason for g in gaps),
            next_action='Interview Agent should clarify the listed evidence gaps.' if gaps else '',
        )

    @staticmethod
    def _finding(raw, document):
        evidence = tuple(EvidenceRef(
            document_id=document.document_id,
            source_hash=document.source_hash,
            quote=raw.get('evidence', ''),
        ) for _ in [0] if raw.get('evidence'))
        status = raw.get('status', 'unknown')
        if status == 'missing':
            status = 'unknown'
        if status == 'partial':
            status = 'partially_supported'
        return FindingResponse(
            criterion_id=raw.get('criterion_id', ''),
            status=status,
            finding=raw.get('finding') or raw.get('evidence') or 'No evidence was found.',
            evidence=evidence,
            limitations=tuple(raw.get('limitations') or ()),
        )


class ScreeningService:
    """Application use case; the ranking engine is injected by infrastructure."""

    def __init__(self, ranker):
        self._ranker = ranker

    def execute(self, request: ScreeningRequest) -> ScreeningResponse:
        requirements, ranked = self._ranker(
            request.model,
            (request.jd_filename, request.jd_content),
            [(cv.filename, cv.content) for cv in request.candidates],
        )
        requirement_dtos = tuple(
            RequirementResponse(name=item['name'], priority=item['priority'])
            for item in requirements['requirements']
        )
        result_dtos = tuple(
            CandidateResultResponse(
                rank=rank,
                filename=result['file'],
                candidate=result.get('candidate', ''),
                score=result.get('score', 0),
                summary=result.get('summary', ''),
                items=tuple(result.get('items', ())),
                error=result.get('error', ''),
            )
            for rank, result in enumerate(ranked, 1)
        )
        return ScreeningResponse(
            job=requirements.get('job', ''),
            requirements=requirement_dtos,
            results=result_dtos,
        )
