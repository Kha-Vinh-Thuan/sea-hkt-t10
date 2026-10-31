from odoo import api, fields, models
from odoo.tools import html2plaintext


class HrJob(models.Model):
    _inherit = 'hr.job'

    # Display-only: a short plain-text excerpt of the JD for the position card.
    aho_jd_excerpt = fields.Char('Tóm tắt JD', compute='_compute_aho_jd_excerpt')

    @api.depends('description')
    def _compute_aho_jd_excerpt(self):
        for job in self:
            text = ' '.join(html2plaintext(job.description or '').split())
            job.aho_jd_excerpt = (text[:177].rstrip() + '...') if len(text) > 180 else text
