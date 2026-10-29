import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .applicant import AGENTS
from .claude import MODELS, ClaudeError, ask

TUNED_AGENTS = ('filter', 'schedule')  # interview + report models live in the T10 Interview AI service
EXPLORE_EVERY = 5    # 1 in 5 candidates tries a neighbouring model
MIN_SAMPLES = 5      # outcomes per model before it can win; ponytail: no significance test, add one when volume allows
TOLERANCE = 0.05     # a cheaper model may be up to 5 points less accurate
GOOD_ENOUGH = 0.8    # champion at/above this explores cheaper, below explores stronger

_logger = logging.getLogger(__name__)

IMPROVER_SCHEMA = {
    'type': 'object',
    'properties': {
        'must_have': {'type': 'string'},
        'filter_threshold': {'type': 'integer'},
        'questions': {'type': 'string'},
        'rubric': {'type': 'string'},
        'rationale': {'type': 'string'},
    },
    'required': ['must_have', 'filter_threshold', 'questions', 'rubric', 'rationale'],
    'additionalProperties': False,
}


class HrJob(models.Model):
    _inherit = 'hr.job'

    ai_enabled = fields.Boolean("AI Recruiting Pipeline")
    ai_must_have = fields.Text(
        "Must-have Requirements",
        help="Used by the Filter agent to score CVs against this job.")
    ai_filter_threshold = fields.Integer("Match Threshold", default=70,
                                         help="CVs scoring at least this (0-100) go on to scheduling.")
    ai_questions = fields.Text(
        "Base Interview Questions",
        default="1. Tell me about yourself and why this role interests you.\n"
                "2. Describe a difficult problem you solved recently. What was your approach?\n"
                "3. Which skills from the job description are you strongest and weakest in?")
    ai_rubric = fields.Text(
        "Scoring Rubric",
        default="- Relevant experience (0-10)\n"
                "- Problem solving (0-10)\n"
                "- Communication clarity (0-10)\n"
                "- Motivation and fit (0-10)")
    ai_max_turns = fields.Integer("Max Candidate Answers", default=10)
    ai_slot_minutes = fields.Integer("Interview Length (min)", default=30)
    ai_join_anytime = fields.Boolean("Demo: join interview anytime",
                                     help="Skip the booked-time window check. For demos and testing only.")
    # Defaults: cheap/fast where the task is simple or latency matters, strongest where judgment matters.
    ai_model_filter = fields.Selection(MODELS, "Filter Model", default='cc/claude-sonnet-5-5', required=True)
    ai_model_schedule = fields.Selection(MODELS, "Schedule Model", default='cc/claude-haiku-5-5', required=True)
    ai_model_report = fields.Selection(MODELS, "Improver Model", default='cc/claude-opus-5-5', required=True)
    ai_industry = fields.Selection([
        ('it', 'IT / Phần mềm'), ('sales', 'Kinh doanh'), ('marketing', 'Marketing'), ('finance', 'Tài chính / Kế toán'),
        ('hr', 'Nhân sự'), ('manufacturing', 'Sản xuất'), ('retail', 'Bán lẻ / F&B'), ('other', 'Khác'),
    ], "Industry", default='other',
        help="Sent to T10 Interview AI: picks its industry interviewer adapter when one is trained.")
    ai_model_auto = fields.Boolean(
        "Auto-tune Models", default=True,
        help="Test a neighbouring model on 1 in 5 candidates and switch to the cheapest model that is as accurate.")
    ai_model_board = fields.Html("Model Leaderboard", compute='_compute_ai_model_board', sanitize=False)
    ai_playbook_version = fields.Integer("Playbook Version", default=1, readonly=True)
    ai_proposal_ids = fields.One2many('t10.ai.playbook.proposal', 'job_id', "AI Proposals")
    # Effectiveness: every metric compares an agent's output with what actually happened next.
    ai_agreement_rate = fields.Float("Report: AI/Human Agreement %", compute='_compute_ai_metrics',
                                     help="Decided candidates where the recruiter's decision matched the AI suggestion.")
    ai_filter_precision = fields.Float("Filter: Precision %", compute='_compute_ai_metrics',
                                       help="Candidates the Filter passed that the recruiter later approved.")
    ai_filter_override_rate = fields.Float("Filter: Overridden %", compute='_compute_ai_metrics',
                                           help="Screened-out CVs the recruiter sent to interview anyway (missed talent).")
    ai_booking_rate = fields.Float("Schedule: Booked %", compute='_compute_ai_metrics',
                                   help="Invited candidates who booked a time without human help.")
    ai_hours_to_book = fields.Float("Schedule: Hours to Book", compute='_compute_ai_metrics')
    ai_no_show_rate = fields.Float("Schedule: No-show %", compute='_compute_ai_metrics')
    ai_completion_rate = fields.Float("Interview: Completed %", compute='_compute_ai_metrics',
                                      help="Booked candidates who finished the AI interview.")
    ai_gray_rate = fields.Float("Report: Gray Zone %", compute='_compute_ai_metrics',
                                help="Interviews the AI scored 57-63 and left to the recruiter.")
    ai_hours_to_report = fields.Float("Pipeline: Hours CV to Report", compute='_compute_ai_metrics')
    ai_cost_per_candidate = fields.Float("Pipeline: AI Cost / Candidate (USD)", compute='_compute_ai_metrics',
                                         digits=(10, 4))
    ai_candidate_count = fields.Integer("Candidates in AI Pipeline", compute='_compute_ai_metrics')

    def _compute_ai_metrics(self):
        def pct(part, whole):
            return 100.0 * len(part) / len(whole) if whole else 0.0

        def avg_hours(records, start, end):
            spans = [(r[end] - r[start]).total_seconds() / 3600 for r in records if r[start] and r[end]]
            return sum(spans) / len(spans) if spans else 0.0

        for job in self:
            apps = self.env['hr.applicant'].with_context(active_test=False).search([
                ('job_id', '=', job.id), ('ai_step', '!=', False)])
            decided = apps.filtered(lambda a: a.ai_human_decision and a.ai_recommendation)
            passed = apps.filtered(lambda a: a.ai_screened_at and (a.ai_match_score >= job.ai_filter_threshold or a.ai_filter_override))
            passed_decided = passed.filtered('ai_human_decision')
            screened_out = apps.filtered(lambda a: a.ai_screened_at and a.ai_match_score < job.ai_filter_threshold)
            invited = apps.filtered('ai_invited_at')
            booked = invited.filtered('ai_booked_at')
            reported = apps.filtered('ai_reported_at')
            job.update({
                'ai_candidate_count': len(apps),
                'ai_agreement_rate': pct(decided.filtered(lambda a: a.ai_human_decision == a.ai_recommendation), decided),
                'ai_filter_precision': pct(passed_decided.filtered(lambda a: a.ai_human_decision == 'approve'), passed_decided),
                'ai_filter_override_rate': pct(screened_out.filtered('ai_filter_override'), screened_out),
                'ai_booking_rate': pct(booked, invited),
                'ai_hours_to_book': avg_hours(booked, 'ai_invited_at', 'ai_booked_at'),
                'ai_no_show_rate': pct(booked.filtered('ai_no_shows'), booked),
                'ai_completion_rate': pct(reported, booked),
                'ai_gray_rate': pct(reported.filtered(lambda a: a.ai_verdict == 'review'), reported),
                'ai_hours_to_report': avg_hours(reported, 'create_date', 'ai_reported_at'),
                'ai_cost_per_candidate': sum(apps.mapped('ai_cost')) / len(apps) if apps else 0.0,
            })

    # ---------------------------------------------------------- model tuning
    # Quality = share of candidates where the agent's work held up (hr.applicant._ai_outcome).
    # Value = cheapest model whose quality is within TOLERANCE of the best, once each has MIN_SAMPLES outcomes.

    def _ai_model_stats(self):
        """{agent: {model: {'n', 'ok', 'cost'}}} over candidates with a known outcome."""
        stats = {}
        apps = self.env['hr.applicant'].with_context(active_test=False).search([
            ('job_id', '=', self.id), ('ai_models', '!=', False)])
        for app in apps:
            for agent, model in (app.ai_models or {}).items():
                outcome = app._ai_outcome(agent)
                if outcome is None:
                    continue
                row = stats.setdefault(agent, {}).setdefault(model, {'n': 0, 'ok': 0, 'cost': 0.0})
                row['n'] += 1
                row['ok'] += outcome
                row['cost'] += (app.ai_costs or {}).get(agent, 0.0)
        return stats

    def _ai_pick_model(self, agent, applicant):
        """Champion for most candidates; every 5th tries a neighbour (cheaper if champion is doing well)."""
        champion = self[f'ai_model_{agent}']
        if not self.ai_model_auto or agent not in TUNED_AGENTS:
            return champion, _("configured")
        if (applicant.id + TUNED_AGENTS.index(agent)) % EXPLORE_EVERY:  # spread challengers across agents
            return champion, _("champion")
        ids = [m for m, _label in MODELS]
        row = self._ai_model_stats().get(agent, {}).get(champion)
        doing_well = not row or row['n'] < MIN_SAMPLES or row['ok'] / row['n'] >= GOOD_ENOUGH
        i = ids.index(champion) + (-1 if doing_well else 1)
        if not 0 <= i < len(ids):
            i = ids.index(champion) + (1 if doing_well else -1)
        return ids[i], _("challenger: testing a %s model", _("cheaper") if i < ids.index(champion) else _("stronger"))

    def _ai_tune_models(self):
        for job in self.filtered('ai_model_auto'):
            for agent, models_ in job._ai_model_stats().items():
                ready = {m: r for m, r in models_.items() if r['n'] >= MIN_SAMPLES and m in dict(MODELS)}
                if agent not in TUNED_AGENTS or not ready:
                    continue
                best = max(r['ok'] / r['n'] for r in ready.values())
                good = [m for m, r in ready.items() if r['ok'] / r['n'] >= best - TOLERANCE]
                pick = min(good, key=lambda m: ready[m]['cost'] / ready[m]['n'])
                current = job[f'ai_model_{agent}']
                if pick != current and current in ready:  # a hand-picked untested model keeps its turn until measured
                    job[f'ai_model_{agent}'] = pick
                    job.message_post(body=_(
                        "AI %(a)s agent switched model %(old)s → %(new)s (quality %(q).0f%% on %(n)s candidates, "
                        "$%(c).4f each).", a=agent, old=current, new=pick, q=100 * ready[pick]['ok'] / ready[pick]['n'],
                        n=ready[pick]['n'], c=ready[pick]['cost'] / ready[pick]['n']))

    def _compute_ai_model_board(self):
        quality = {'filter': _("recruiter agreed"), 'schedule': _("booked"),
}
        for job in self:
            rows = []
            for agent, models_ in sorted(job._ai_model_stats().items()):
                for model, r in sorted(models_.items(), key=lambda kv: -kv[1]['ok'] / kv[1]['n']):
                    star = " ★" if job[f'ai_model_{agent}'] == model else ""
                    per_ok = f"${r['cost'] / r['ok']:.4f}" if r['ok'] else "-"
                    rows.append(f"<tr><td>{agent}</td><td>{model}{star}</td><td>{r['n']}</td>"
                                f"<td>{100 * r['ok'] / r['n']:.0f}% {quality.get(agent, '')}</td>"
                                f"<td>${r['cost'] / r['n']:.4f}</td><td>{per_ok}</td></tr>")
            job.ai_model_board = (
                "<table class='table table-sm'><tr><th>Agent</th><th>Model</th><th>Candidates</th><th>Quality</th>"
                "<th>Cost / candidate</th><th>Cost / correct result</th></tr>%s</table>" % "".join(rows)
            ) if rows else _("<p>No finished candidates yet.</p>")

    def action_ai_upload_cvs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Upload CVs"),
            'res_model': 't10.ai.cv.upload',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }

    def action_ai_screen_existing(self):
        applicants = self.env['hr.applicant'].search([
            ('job_id', 'in', self.ids), ('ai_step', '=', False), ('application_status', '=', 'ongoing')])
        applicants.ai_step = 'new'
        self.env.ref('t10_ai_interview.ir_cron_ai_orchestrator')._trigger()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': _("%s applicants queued for AI screening.", len(applicants)), 'type': 'success'}}

    def action_ai_improve(self):
        for job in self:
            job._ai_improve()

    @api.model
    def _cron_ai_improve(self):
        for job in self.search([('ai_enabled', '=', True)]):
            try:
                job._ai_improve()
            except (ClaudeError, UserError) as e:
                _logger.info("AI improve skipped for job %s: %s", job.id, e)

    def _ai_improve(self):
        """Report agent, learning half: compare AI verdicts with recruiter decisions, propose a better playbook."""
        self.ensure_one()
        if self.ai_proposal_ids.filtered(lambda p: p.state == 'proposed'):
            raise UserError(_("A proposal is already waiting for review."))
        applicants = self.env['hr.applicant'].with_context(active_test=False).search([
            ('job_id', '=', self.id), ('ai_playbook_version', '=', self.ai_playbook_version),
            ('ai_step', '!=', False)])
        decided = applicants.filtered('ai_human_decision')
        if len(decided) < 3:
            raise UserError(_("Need at least 3 candidates decided by a recruiter on the current playbook (have %s).", len(decided)))
        last = self.ai_proposal_ids.filtered(lambda p: p.base_version == self.ai_playbook_version)[:1]
        if last and len(decided) < last.sample_size + 3:
            raise UserError(_("Waiting for 3 new decisions since the last proposal."))
        cases = [{
            'cv_match_score': a.ai_match_score,
            'cv_match_summary': a.ai_match_summary,
            'screened_out_by_ai_but_recruiter_overrode': a.ai_filter_override,
            'interview_score': a.ai_score or None,
            'ai_recommendation': a.ai_recommendation or None,
            'recruiter_decision': a.ai_human_decision,
            'refuse_reason': a.refuse_reason_id.name or None,
            'recruiter_feedback_on_ai': a.ai_feedback or None,
            'interview_summary': a.ai_summary or None,
        } for a in decided]
        result = ask(
            system=(
                "You improve an automated recruiting playbook: CV must-have requirements, CV match threshold, "
                "interview questions and scoring rubric. You get past candidates with the AI's CV match score, "
                "interview score and recommendation next to the recruiter's real decision and feedback. "
                "Find where the AI disagreed with recruiters (false positives and false negatives), which "
                "requirements or questions failed to separate strong from weak candidates, and which rubric "
                "criteria were miscalibrated. Return revised versions in the same plain-text format and a short "
                "rationale citing the evidence. Judge only job-relevant ability; never add criteria about age, "
                "gender, ethnicity, religion, health, family status or other protected attributes."
            ),
            messages=[{'role': 'user', 'content': json.dumps({
                'job': self.name,
                'job_description': self.description and str(self.description),
                'current': {
                    'must_have': self.ai_must_have, 'filter_threshold': self.ai_filter_threshold,
                    'questions': self.ai_questions, 'rubric': self.ai_rubric,
                },
                'cases': cases,
            }, ensure_ascii=False)}],
            schema=IMPROVER_SCHEMA,
            effort='high',
            model=self.ai_model_report,
        )
        result.pop('_cost', None)
        result.pop('_model', None)
        return self.env['t10.ai.playbook.proposal'].create({
            'job_id': self.id,
            'base_version': self.ai_playbook_version,
            'must_have': result['must_have'],
            'filter_threshold': max(0, min(100, result['filter_threshold'])),
            'questions': result['questions'],
            'rubric': result['rubric'],
            'rationale': result['rationale'],
            'sample_size': len(decided),
            'agreement_before': 100.0 * len(decided.filtered(lambda a: a.ai_human_decision == a.ai_recommendation)) / len(decided),
        })


class T10AiPlaybookProposal(models.Model):
    _name = 't10.ai.playbook.proposal'
    _description = 'AI Recruiting Playbook Proposal'
    _order = 'id desc'

    job_id = fields.Many2one('hr.job', required=True, ondelete='cascade')
    base_version = fields.Integer(readonly=True)
    must_have = fields.Text()
    filter_threshold = fields.Integer()
    questions = fields.Text()
    rubric = fields.Text()
    rationale = fields.Text(readonly=True)
    sample_size = fields.Integer(readonly=True)
    agreement_before = fields.Float("Agreement % before", readonly=True,
                                    help="AI/recruiter agreement on the playbook this proposal replaces.")
    state = fields.Selection([
        ('proposed', 'Proposed'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='proposed', readonly=True)

    def action_approve(self):
        for proposal in self.filtered(lambda p: p.state == 'proposed'):
            job = proposal.job_id
            job.message_post(body=_(
                "AI playbook v%(old)s replaced by v%(new)s. Previous: threshold %(t)s\n"
                "Must-have:\n%(m)s\nQuestions:\n%(q)s\nRubric:\n%(r)s",
                old=job.ai_playbook_version, new=job.ai_playbook_version + 1, t=job.ai_filter_threshold,
                m=job.ai_must_have, q=job.ai_questions, r=job.ai_rubric))
            job.write({
                'ai_must_have': proposal.must_have,
                'ai_filter_threshold': proposal.filter_threshold,
                'ai_questions': proposal.questions,
                'ai_rubric': proposal.rubric,
                'ai_playbook_version': job.ai_playbook_version + 1,
            })
            proposal.state = 'approved'

    def action_reject(self):
        self.filtered(lambda p: p.state == 'proposed').state = 'rejected'


class T10AiLog(models.Model):
    _name = 't10.ai.log'
    _description = 'AI Agent Activity'
    _order = 'id desc'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade', index=True)
    job_id = fields.Many2one(related='applicant_id.job_id', store=True)
    agent = fields.Selection(AGENTS, "From", required=True)
    to_agent = fields.Selection(AGENTS, "To", help="Set when one agent hands work or information to another.")
    message = fields.Text(required=True)
