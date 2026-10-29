import os

from odoo import _, fields, models
from odoo.exceptions import UserError


class T10AiCvUpload(models.TransientModel):
    _name = 't10.ai.cv.upload'
    _description = 'Upload CVs for AI screening'

    job_id = fields.Many2one('hr.job', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string="CV files")

    def action_upload(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_("Add at least one CV."))
        if not self.job_id.ai_enabled:
            raise UserError(_("Enable the AI Recruiting Pipeline on this job first."))
        applicants = self.env['hr.applicant']
        for attachment in self.attachment_ids:
            applicant = applicants.create({
                'partner_name': os.path.splitext(attachment.name)[0],  # Filter agent replaces with the real name
                'job_id': self.job_id.id,
            })
            attachment.write({'res_model': 'hr.applicant', 'res_id': applicant.id})
            applicants |= applicant
        self.env.ref('t10_ai_interview.ir_cron_ai_orchestrator')._trigger()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Uploaded CVs"),
            'res_model': 'hr.applicant',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', applicants.ids)],
        }
