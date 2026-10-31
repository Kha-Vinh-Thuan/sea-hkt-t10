from odoo.tests.common import TransactionCase


class TestRagReportAdapter(TransactionCase):
    def test_compile_report_from_ui_bundle(self):
        report = self.env['rag.report'].create({
            'name': 'Adapter test',
            'run_id': 'run-ui-1',
            'candidate_id': 'candidate-1',
            'role_id': 'backend',
            'role_version': 'v1',
            'assignment': 'Review candidate evidence',
            'bundle': [{
                'name': 'filter',
                'status': 'Complete',
                'requested': True,
                'summary': 'Evidence review completed.',
                'findings': [{
                    'criterion_id': 'java',
                    'status': 'supported',
                    'evidence': [{'document_id': 'cv-1', 'quote': 'Java'}],
                }],
                'artifact_refs': [{'artifact_id': 'filter-1'}],
            }, {
                'name': 'interview',
                'status': 'Needs input',
                'requested': True,
                'evidence_gaps': [{'criterion_id': 'profiling'}],
                'open_items': ['Candidate answer is required.'],
                'next_action': 'Collect the submitted answer.',
            }],
        })

        self.assertTrue(report.action_compile())
        self.assertEqual(report.report_status, 'Complete')
        self.assertEqual(report.overall_status, 'Needs input')
        self.assertIn('Candidate answer is required.', report.open_items)
        self.assertIn('Orchestrator', report.next_actions)
        self.assertEqual(report.report_json['findings'][0]['criterion_id'], 'java')

    def test_invalid_bundle_is_reported_as_needs_input(self):
        report = self.env['rag.report'].create({
            'name': 'Invalid adapter test',
            'run_id': 'run-ui-2',
            'candidate_id': 'candidate-2',
            'assignment': 'Review candidate evidence',
            'bundle': [{}],
        })
        self.assertTrue(report.action_compile())
        self.assertEqual(report.report_status, 'Needs input')
        self.assertEqual(report.overall_status, 'Needs input')
