from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from ..models.claude import ClaudeError


class AiInterviewController(http.Controller):

    def _applicant(self, token):
        if not token or len(token) < 32:
            return None
        return request.env['hr.applicant'].sudo().search([('ai_token', '=', token)], limit=1) or None

    def _run(self, token, fn):
        applicant = self._applicant(token)
        if not applicant:
            return {'error': 'closed'}
        try:
            return fn(applicant)
        except ClaudeError:
            return {'error': 'ai'}
        except UserError as e:
            return {'error': 'closed', 'message': str(e)}

    @http.route('/interview/<string:token>', type='http', auth='public')
    def page(self, token, **kw):
        applicant = self._applicant(token)
        if not applicant:
            return request.render('t10_ai_interview.interview_closed')
        if applicant.ai_step == 'interviewing' or (applicant.ai_step == 'scheduled' and applicant._ai_can_join()):
            try:  # the interview itself runs on the standalone T10 Interview AI
                return request.redirect(applicant._ai_open_interview(), local=False)
            except UserError:
                return request.render('t10_ai_interview.interview_closed')
        if applicant.ai_step in ('scheduling', 'scheduled'):
            mode = 'schedule'
        else:
            return request.render('t10_ai_interview.interview_closed')
        return request.render('t10_ai_interview.interview_page', {
            'applicant': applicant,
            'token': token,
            'mode': mode,
            'slots': applicant._ai_public_slots(),
            'booked': applicant.ai_event_id and applicant._ai_fmt(applicant.ai_event_id.start),
            'tz': applicant._ai_tz().key,
        })

    @http.route('/interview/<string:token>/pick', type='jsonrpc', auth='public')
    def pick(self, token, index=-1):
        return self._run(token, lambda a: a._ai_candidate_pick(int(index)))

    @http.route('/interview/<string:token>/schedule', type='jsonrpc', auth='public')
    def schedule(self, token, message=''):
        message = (message or '').strip()
        if not message:
            return {'error': 'empty'}
        return self._run(token, lambda a: a._ai_candidate_message(message))
