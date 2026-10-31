from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Display-only summaries. Never advance stages, schedule sessions, or call providers.
    aho_interview_state = fields.Selection([
        ('none', 'Chưa tạo phỏng vấn'), ('ready', 'Sẵn sàng'),
        ('running', 'Đang phỏng vấn'), ('done', 'Đang tạo báo cáo'),
        ('reported', 'Có báo cáo'), ('error', 'Lỗi xử lý'),
    ], string='Phỏng vấn AI', compute='_compute_aho_interview_summary')
    aho_next_action = fields.Char('Việc tiếp theo', compute='_compute_aho_interview_summary')

    @api.depends('active', 'recruiter_id', 'rag_interview_ids', 'rag_interview_ids.state')
    def _compute_aho_interview_summary(self):
        actions = {
            'none': 'Xem hồ sơ và chuẩn bị phỏng vấn',
            'ready': 'Chờ ứng viên bắt đầu phỏng vấn',
            'running': 'Chờ ứng viên hoàn tất phỏng vấn',
            'done': 'Chờ báo cáo phỏng vấn',
            'reported': 'Xem báo cáo và cập nhật giai đoạn tuyển dụng',
            'error': 'Kiểm tra lỗi trong phiên phỏng vấn',
        }
        for applicant in self:
            session = applicant.rag_interview_ids.sorted('id', reverse=True)[:1]
            state = session.state if session else 'none'
            applicant.aho_interview_state = state
            applicant.aho_next_action = (
                'Hồ sơ đã lưu trữ' if not applicant.active else
                'Cần phân công HR phụ trách' if not applicant.recruiter_id else
                actions.get(state, 'Xem hồ sơ ứng viên')
            )
