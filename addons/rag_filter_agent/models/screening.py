import os
import hashlib

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..rag_filter_application.dto.requests import CriterionRequest, DocumentRequest, FilterRequest
from ..rag_filter_application.services.screening_service import FilterService
from . import matcher

DEFAULT_MODEL = 'gpt-6.1-sol'  # ponytail: overridable in Settings (rag_filter.model); must accept PDF file inputs

class RagFilter(models.Model):
    _name = 'rag.filter'
    _description = 'CV Screening (JD match)'
    _order = 'id desc'

    name = fields.Char(required=True, default=lambda s: _('CV Screening'))
    jd_file = fields.Binary("JD (PDF)", required=True, attachment=True)
    jd_filename = fields.Char()
    cv_ids = fields.Many2many('ir.attachment', string="CVs (PDF)")
    job = fields.Char(readonly=True)
    requirements = fields.Text(readonly=True)
    role_id = fields.Char("Role ID", default='job-description')
    role_version = fields.Char(readonly=True)
    result_ids = fields.One2many('rag.filter.result', 'filter_id', "Evidence Review", readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    def _configure(self):
        # same raw read as rag_interview_agent: this Odoo build has no ir.config_parameter.get_param
        self.env.cr.execute("SELECT key, value FROM ir_config_parameter WHERE key IN ('rag_filter.openai_key', 'rag_filter.model')")
        params = dict(self.env.cr.fetchall())
        matcher.configure_key(params.get('rag_filter.openai_key') or os.environ.get('OPENAI_API_KEY', ''))
        return params.get('rag_filter.model') or DEFAULT_MODEL

    def action_match(self):
        self.ensure_one()
        cvs = [(a.name, a.raw.content) for a in self.cv_ids if a.mimetype == 'application/pdf' and a.raw]
        if not cvs:
            raise UserError(_("Upload at least one CV in PDF."))
        jd = self.jd_file
        if not jd or jd.mimetype != 'application/pdf':
            raise UserError(_("Upload the JD in PDF."))
        try:
            model = self._configure()
            extracted = matcher.requirements(model, self.jd_filename or 'job-description.pdf', jd.content)
            role_version = hashlib.sha256(jd.content).hexdigest()
            criteria = tuple(CriterionRequest(
                criterion_id=f'req-{number}', label=item['name'], description=item['name'],
                required=item['priority'] == 'must',
            ) for number, item in enumerate(extracted['requirements'], 1))
            service = FilterService(matcher.review)
            handoffs = []
            for number, (name, content) in enumerate(cvs, 1):
                document_hash = hashlib.sha256(content).hexdigest()
                request = FilterRequest(
                    run_id=str(self.id), candidate_id=name, role_id=self.role_id or 'job-description',
                    role_version=role_version, criteria=criteria,
                    documents=(DocumentRequest(name, name, content, document_hash),), model=model,
                )
                handoffs.append(service.execute(request))
        except matcher.MatchError as e:
            raise UserError(str(e)) from e

        def lines(handoff, statuses):
            return '\n'.join(
                f"[{item.criterion_id}] {item.finding}"
                for item in handoff.findings if item.status in statuses
            )

        self.result_ids.unlink()
        self.write({
            'job': extracted['job'], 'role_version': role_version, 'state': 'done',
            'requirements': '\n'.join(f"[{r.criterion_id}] {r.label}" for r in criteria),
            'result_ids': [(0, 0, {
                'sequence': number, 'file': handoff.candidate_id, 'candidate': handoff.candidate_id,
                'status': handoff.status, 'summary': handoff.summary,
                'error': '', 'details': handoff.to_dict(),
                'matched': lines(handoff, ('supported',)),
                'partial': lines(handoff, ('partially_supported',)),
                'missing': lines(handoff, ('unknown', 'conflicting')),
                'limitations': '\n'.join(handoff.limitations),
                'evidence_gaps': '\n'.join(g.reason for g in handoff.evidence_gaps),
            }) for number, handoff in enumerate(handoffs, 1)],
        })

class RagFilterResult(models.Model):
    _name = 'rag.filter.result'
    _description = 'CV Screening Result'
    _order = 'sequence'

    filter_id = fields.Many2one('rag.filter', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer()
    file = fields.Char("CV File")
    candidate = fields.Char()
    status = fields.Selection([('Complete', 'Complete'), ('Needs input', 'Needs input'), ('Failed', 'Failed')])
    summary = fields.Text()
    matched = fields.Text()
    partial = fields.Text()
    missing = fields.Text()
    limitations = fields.Text()
    evidence_gaps = fields.Text()
    details = fields.Json()
    error = fields.Text()
