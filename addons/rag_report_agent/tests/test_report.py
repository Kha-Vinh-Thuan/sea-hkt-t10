import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from application.dto.requests import BranchHandoff, ReportRequest
from application.services.report_service import ReportService


def test_report_preserves_findings_and_artifacts():
    response = ReportService().execute(ReportRequest(
        run_id='run-1', assignment='Review candidate', candidate_id='candidate-1',
        branches=(BranchHandoff(
            name='filter', status='Complete', requested=True,
            summary='Evidence review completed.',
            findings=({'criterion_id': 'java', 'status': 'supported', 'evidence': [{'document_id': 'cv-1'}]},),
            artifact_refs=({'artifact_id': 'filter-1'},),
        ),),
    ))
    payload = response.to_dict()
    assert response.overall_status == 'Complete'
    assert payload['findings'][0]['criterion_id'] == 'java'
    assert payload['artifact_refs'][0]['artifact_id'] == 'filter-1'


def test_report_keeps_incomplete_branch_visible_and_does_not_claim_success():
    response = ReportService().execute(ReportRequest(
        run_id='run-2', assignment='Review candidate and interview', candidate_id='candidate-2',
        branches=(
            BranchHandoff(name='filter', status='Complete', requested=True, summary='Done.'),
            BranchHandoff(name='interview', status='Needs input', requested=True,
                          evidence_gaps=({'criterion_id': 'profiling'},),
                          open_items=('Candidate answer is still required.',),
                          next_action='Collect the submitted answer.'),
            BranchHandoff(name='schedule', status='Complete', requested=False, summary='Not requested.'),
        ),
    ))
    assert response.report_status == 'Complete'
    assert response.overall_status == 'Needs input'
    assert response.branch_states[2]['requested'] is False
    assert response.evidence_gaps[0]['criterion_id'] == 'profiling'
    assert response.next_actions[0]['owner'] == 'Orchestrator'


def test_failed_requested_branch_remains_failed():
    response = ReportService().execute(ReportRequest(
        run_id='run-3', assignment='Review candidate', candidate_id='candidate-3',
        branches=(BranchHandoff(name='filter', status='Failed', requested=True, open_items=('Provider error',)),),
    ))
    assert response.overall_status == 'Failed'
    assert response.open_items == ('Provider error',)
