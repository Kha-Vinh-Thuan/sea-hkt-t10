from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

ASK = 'odoo.addons.t10_ai_interview.models.applicant.ask'
T10 = 'odoo.addons.t10_ai_interview.models.t10.call'
ASK_JOB = 'odoo.addons.t10_ai_interview.models.job.ask'
REPORT = {'score': 80, 'verdict': 'pass', 'summary': 'good', 'criteria': [], 'next_round_focus': ['system design'],
          'integrity': {'score': 95, 'summary': 'ok', 'events': {}, 'review': False}}


@tagged('post_install', '-at_install')
class TestAiPipeline(TransactionCase):

    def setUp(self):
        super().setUp()
        self.job = self.env['hr.job'].create({
            'name': 'Dev', 'ai_enabled': True, 'ai_max_turns': 2, 'ai_filter_threshold': 70, 'ai_model_auto': False})
        self.no_trigger = patch.object(type(self.env['ir.cron']), '_trigger')
        self.no_trigger.start()
        self.addCleanup(self.no_trigger.stop)
        self.t10 = patch(T10, side_effect=self._t10)  # fake T10 Interview AI service
        self.t10_call = self.t10.start()
        self.addCleanup(self.t10.stop)
        self.status, self.report = 'in_progress', REPORT

    def _t10(self, method, path, payload=None, timeout=30):
        if path == '/v1/sessions':
            return {'id': 'is_1', 'join_url': 'http://t10/join/tok', 'embed_token': 'tok'}
        if path.endswith('/decision'):
            return {'used_for_learning': True}
        return {'status': self.status, 'report': self.report if self.status == 'reported' else None,
                'transcript': [{'role': 'assistant', 'content': 'Q?'}, {'role': 'user', 'content': 'A'}]}

    def _applicant_with_cv(self, text='Python dev, 5 years'):
        wizard = self.env['t10.ai.cv.upload'].create({
            'job_id': self.job.id,
            'attachment_ids': [(0, 0, {'name': 'cv_an.txt', 'mimetype': 'text/plain', 'raw': text.encode()})],
        })
        return self.env['hr.applicant'].browse(wizard.action_upload()['domain'][0][2]).sudo()

    def _filter(self, app, score, claims=('Led a team of 10',)):
        with patch(ASK, return_value={'name': 'Nguyen An', 'email': 'an@example.com', 'phone': '',
                                      'match_score': score, 'summary': 's', 'strengths': ['a'], 'gaps': ['b'],
                                      'verify_claims': list(claims), '_cost': 0.01}) as ask:
            app._ai_agent_filter()
        return ask

    def _book_now(self, app):
        app._ai_agent_schedule_invite()
        app._ai_candidate_pick(0)
        app.ai_event_id.write({'start': fields.Datetime.now(), 'stop': fields.Datetime.now() + timedelta(minutes=30)})

    def _interview(self, app, report=REPORT):
        """Candidate joins the T10 room, finishes, the orchestrator picks the report up."""
        self.assertEqual(app._ai_open_interview(), 'http://t10/join/tok')
        self.status = 'in_progress'
        app._ai_agent_interview_poll()
        self.assertEqual(app.ai_step, 'interviewing')
        self.status, self.report = 'reported', report
        app._ai_agent_interview_poll()

    def test_full_pipeline_and_handoffs(self):
        app = self._applicant_with_cv()
        self.assertEqual(app.ai_step, 'new')

        # 1. Filter: reads CV, extracts contact, hands claims to Interview
        ask = self._filter(app, 85)
        self.assertIn('Python dev', ask.call_args.kwargs['messages'][0]['content'][0]['text'])
        self.assertEqual(ask.call_args.kwargs['model'], app.ai_models['filter'])
        self.assertEqual((app.ai_step, app.partner_name, app.email_from), ('passed', 'Nguyen An', 'an@example.com'))
        self.assertIn('Led a team', app.ai_verify_claims)

        # 2. Schedule: slots, free-text exception, booking
        app._ai_agent_schedule_invite()
        self.assertEqual((app.ai_step, len(app.ai_slots)), ('scheduling', 3))
        with patch(ASK, return_value={'action': 'unclear', 'slot_index': -1, 'proposed_start_local': '', 'reply': 'Which day?'}):
            self.assertEqual(app._ai_candidate_message('I am busy')['reply'], 'Which day?')
        self.assertTrue(app._ai_candidate_pick(0)['booked'])
        with patch(ASK, return_value={'action': 'propose', 'slot_index': -1,
                                      'proposed_start_local': '2030-01-05 03:00', 'reply': 'ok'}):
            self.assertTrue(app._ai_candidate_message('Saturday 3am?')['slots'])  # weekend 3am refused

        # 3. Interview on T10: full context incl. the Filter's claims; Odoo only collects the report
        self._interview(app)
        ctx = next(c.args[2]['context'] for c in self.t10_call.call_args_list if c.args[1] == '/v1/sessions')
        self.assertEqual((ctx['job_title'], ctx['max_answers'], ctx['verify_claims']), ('Dev', 2, ['Led a team of 10']))
        self.assertEqual((app.ai_step, app.ai_score, app.ai_verdict, app.ai_recommendation),
                         ('reported', 80, 'pass', 'approve'))
        self.assertIn('Candidate: A', app.ai_transcript_text)
        app.action_ai_approve()
        self.assertEqual((app.ai_step, app.ai_human_decision), ('decided', 'approve'))

        handoffs = {(l.agent, l.to_agent) for l in app.ai_log_ids if l.to_agent}
        self.assertTrue({('filter', 'schedule'), ('filter', 'interview'), ('schedule', 'interview'),
                         ('report', 'recruiter'), ('recruiter', 'report')} <= handoffs)
        decision = next(c.args for c in self.t10_call.call_args_list if c.args[1].endswith('/decision'))
        self.assertEqual(decision[2]['decision'], 'hire')  # T10 learns from it if the candidate consented
        self.assertAlmostEqual(app.ai_cost, 0.01)

        # Effectiveness metrics
        self.assertEqual(self.job.ai_agreement_rate, 100.0)
        self.assertEqual(self.job.ai_filter_precision, 100.0)
        self.assertEqual(self.job.ai_booking_rate, 100.0)
        self.assertEqual(self.job.ai_completion_rate, 100.0)
        self.assertAlmostEqual(self.job.ai_cost_per_candidate, 0.01)

    def test_gray_zone_and_service_down(self):
        app = self.env['hr.applicant'].create({'partner_name': 'Demo', 'job_id': self.job.id})
        self.t10_call.side_effect = UserError('T10 Interview AI unavailable')
        with self.assertRaises(UserError):
            app.action_ai_interview_now()
        self.t10_call.side_effect = self._t10
        app.action_ai_interview_now()
        self._interview(app, dict(REPORT, score=60, verdict='review'))
        self.assertEqual((app.ai_verdict, app.ai_recommendation), ('review', False))  # recruiter decides
        self.assertEqual(self.job.ai_gray_rate, 100.0)
        other = self.env['hr.applicant'].create({'partner_name': 'B', 'job_id': self.job.id})
        other.action_ai_interview_now()
        self.status = 'report_failed'
        with self.assertRaises(UserError):
            other._ai_agent_interview_poll()

    def test_filter_reject_override_and_metrics(self):
        app = self._applicant_with_cv()
        self._filter(app, 40)
        self.assertEqual((app.ai_step, app.ai_recommendation), ('screened_out', 'reject'))
        app.action_ai_override_filter()
        self.assertEqual((app.ai_step, app.ai_filter_override), ('passed', True))
        self.assertEqual(self.job.ai_filter_override_rate, 100.0)

    def test_decline_no_show_and_bad_cv(self):
        app = self._applicant_with_cv()
        self._filter(app, 90)
        app._ai_agent_schedule_invite()
        with patch(ASK, return_value={'action': 'decline', 'slot_index': -1, 'proposed_start_local': '', 'reply': 'Bye'}):
            self.assertTrue(app._ai_candidate_message('I took another job')['closed'])
        self.assertEqual(app.ai_step, 'declined')

        late = self._applicant_with_cv()
        self._filter(late, 90)
        self._book_now(late)
        late._ai_agent_schedule_no_show()
        self.assertEqual(late.ai_step, 'scheduling')  # first no-show: re-invited
        late._ai_agent_schedule_no_show()
        self.assertEqual(late.ai_step, 'no_show')     # second: handed to recruiter
        self.assertEqual(self.job.ai_no_show_rate, 100.0)

        bad = self._applicant_with_cv()
        bad.attachment_ids.mimetype = 'application/zip'
        with self.assertRaises(UserError):
            bad._ai_agent_filter()

    def test_improver(self):
        with self.assertRaises(UserError):
            self.job._ai_improve()
        for decision in ('approve', 'reject', 'reject'):
            app = self._applicant_with_cv()
            app.write({'ai_step': 'decided', 'ai_human_decision': decision, 'ai_recommendation': 'approve',
                       'ai_playbook_version': 1})
        self.assertAlmostEqual(self.job.ai_agreement_rate, 100 / 3, places=1)
        with patch(ASK_JOB, return_value={'must_have': 'm', 'filter_threshold': 80, 'questions': 'q',
                                          'rubric': 'r', 'rationale': 'why', '_cost': 0.1}):
            proposal = self.job._ai_improve()
        self.assertAlmostEqual(proposal.agreement_before, 100 / 3, places=1)
        proposal.action_approve()
        self.assertEqual((self.job.ai_filter_threshold, self.job.ai_playbook_version), (80, 2))

    def test_model_tuning_and_lessons(self):
        """Cheaper model that is as accurate takes over; wrong verdicts become lessons for the next candidate."""
        self.job.ai_model_auto = True
        sonnet, haiku = 'cc/claude-sonnet-5-5', 'cc/claude-haiku-5-5'
        for i in range(10):  # 5 per model, same 80% accuracy, haiku 20x cheaper
            model, cost = (sonnet, 0.02) if i < 5 else (haiku, 0.001)
            self._applicant_with_cv().write({
                'ai_models': {'filter': model}, 'ai_costs': {'filter': cost}, 'ai_step': 'decided',
                'ai_human_decision': 'approve' if i % 5 else 'reject', 'ai_recommendation': 'approve'})
        self.assertIn(haiku, self.job.ai_model_board)
        self.job._ai_tune_models()
        self.assertEqual(self.job.ai_model_filter, haiku)

        # explore: 1 in EXPLORE_EVERY candidates tries a neighbour, the rest use the champion
        picks = {self.job._ai_pick_model('filter', self.env['hr.applicant'].browse(i))[0] for i in range(5)}
        self.assertEqual(len(picks), 2)

        # the 2 filter mistakes (passed, recruiter rejected) are fed to the next screening
        app = self._applicant_with_cv()
        ask = self._filter(app, 85)
        self.assertEqual(len(app._ai_lessons('filter')), 2)
        self.assertIn('reject', ask.call_args.kwargs['messages'][0]['content'][-1]['text'])

    def test_interview_now(self):
        """MVP demo: one button on any applicant opens the T10 interview room, report follows when it ends."""
        self.job.ai_enabled = False
        app = self.env['hr.applicant'].create({'partner_name': 'Demo', 'job_id': self.job.id})
        action = app.action_ai_interview_now()
        self.assertEqual((app.ai_step, self.job.ai_enabled, action['url']), ('interviewing', True, 'http://t10/join/tok'))
        self.assertEqual(app.action_ai_interview_now()['url'], action['url'])  # reopen keeps the same room
        self.assertEqual(sum(c.args[1] == '/v1/sessions' for c in self.t10_call.call_args_list), 1)
        self._interview(app, dict(REPORT, integrity={'score': 40, 'summary': 'Có người khác', 'events': {}, 'review': True}))
        self.assertEqual((app.ai_step, app.ai_integrity_score), ('reported', 40))

    def test_t10_client_needs_key(self):
        """Odoo is a plain tenant of the standalone service: no key, no call."""
        from odoo.addons.t10_ai_interview.models import t10
        self.t10.stop()
        self.addCleanup(self.t10.start)
        with patch.dict('os.environ', {'T10_API_KEY': ''}), self.assertRaises(UserError):
            t10.call('GET', '/v1/sessions')
        with patch.dict('os.environ', {'T10_API_KEY': 'k'}), patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"ok": 1}'
            self.assertEqual(t10.call('GET', '/v1/sessions'), {'ok': 1})
        self.assertEqual(urlopen.call_args.args[0].get_header('Authorization'), 'Bearer k')
