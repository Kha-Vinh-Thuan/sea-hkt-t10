import json

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..application.dto.requests import BranchHandoff, ReportRequest
from ..application.services.report_service import ReportService


class RagReport(models.Model):
    _name = 'rag.report'
    _description = 'Evidence Report'
    _order = 'id desc'

    name = fields.Char(required=True, default=lambda self: _('Recruiting Report'))
    run_id = fields.Char(required=True, index=True)
    candidate_id = fields.Char(required=True)
    role_id = fields.Char()
    role_version = fields.Char()
    assignment = fields.Text(required=True)
    bundle = fields.Json(required=True, help='Validated specialist handoffs supplied by Orchestrator.')
    report_status = fields.Selection([('Complete', 'Complete'), ('Needs input', 'Needs input')], readonly=True)
    overall_status = fields.Selection([
        ('Complete', 'Complete'), ('Needs input', 'Needs input'), ('Failed', 'Failed')
    ], readonly=True)
    summary = fields.Text(readonly=True)
    report_json = fields.Json(readonly=True)
    limitations = fields.Text(readonly=True)
    open_items = fields.Text(readonly=True)
    next_actions = fields.Text(readonly=True)

    def action_compile(self):
        self.ensure_one()
        branches = tuple(BranchHandoff(
            name=item.get('name', ''), status=item.get('status', 'Needs input'),
            requested=bool(item.get('requested')), summary=item.get('summary', ''),
            findings=tuple(item.get('findings') or ()), evidence_gaps=tuple(item.get('evidence_gaps') or ()),
            limitations=tuple(item.get('limitations') or ()), open_items=tuple(item.get('open_items') or ()),
            next_action=item.get('next_action', ''), artifact_refs=tuple(item.get('artifact_refs') or ()),
        ) for item in (self.bundle or []))
        try:
            response = ReportService().execute(ReportRequest(
                run_id=self.run_id, assignment=self.assignment, candidate_id=self.candidate_id,
                role_id=self.role_id or '', role_version=self.role_version or '', branches=branches,
            ))
        except ValueError as error:
            raise UserError(str(error)) from error
        self.write({
            'report_status': response.report_status,
            'overall_status': response.overall_status,
            'summary': response.summary,
            'report_json': response.to_dict(),
            'limitations': '\n'.join(response.limitations),
            'open_items': '\n'.join(response.open_items),
            'next_actions': '\n'.join(f"[{item['owner']}] {item['action']}" for item in response.next_actions),
        })
        return True
