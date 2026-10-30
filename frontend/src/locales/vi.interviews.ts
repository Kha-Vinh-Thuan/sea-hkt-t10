// Vietnamese texts for the interviews screens; key = the English text passed to t().
export default {
  // InterviewDialog
  'Reschedule interview': 'Đổi lịch phỏng vấn', 'Schedule interview': 'Đặt lịch phỏng vấn',
  'I pick the time': 'Tôi chọn giờ', 'Let the candidate choose': 'Để ứng viên chọn',
  'Someone else (type name and email)': 'Người khác (nhập tên và email)', Start: 'Bắt đầu',
  'Interviewer name': 'Tên người phỏng vấn', 'Interviewer email': 'Email người phỏng vấn',
  'Choose an interviewer from the list to see their free times.': 'Chọn người phỏng vấn trong danh sách để xem giờ rảnh.',
  'Tick the times to offer; the candidate gets an email and picks one':
    'Chọn các khung giờ đề xuất; ứng viên nhận email và chọn một',
  'No free time in the next 7 days.': 'Không có giờ rảnh trong 7 ngày tới.',
  'Meeting link or room': 'Link họp hoặc phòng',
  'Leave empty to use a Google Meet link when the interviewer connected Google Calendar':
    'Để trống để dùng link Google Meet nếu người phỏng vấn đã kết nối Google Calendar',
  '{n} min': '{n} phút',
  'Email {n} time to candidate': 'Gửi {n} khung giờ cho ứng viên',
  'Email {n} times to candidate': 'Gửi {n} khung giờ cho ứng viên',
  'Update and send invite': 'Cập nhật và gửi lời mời', 'Book and send invite': 'Đặt lịch và gửi lời mời',
  // TeamCalendar
  'Previous week': 'Tuần trước', 'Next week': 'Tuần sau',
  'No Google Calendar: {names}': 'Chưa có Google Calendar: {names}',
  'Google Calendar could not be read for {names}; only interviews booked here are shown.':
    'Không đọc được Google Calendar của {names}; chỉ hiện các buổi phỏng vấn đặt tại đây.',
  'Busy: {names}': 'Bận: {names}', 'Free: {names} — click to pick': 'Rảnh: {names} — bấm để chọn',
  'Loading calendars…': 'Đang tải lịch…',
  'busy (interview or Google Calendar; one bar per interviewer)':
    'bận (phỏng vấn hoặc Google Calendar; mỗi người phỏng vấn một vạch)',
  picked: 'đã chọn',
  'white = free, click to pick. The time is re-checked when you book.':
    'trắng = rảnh, bấm để chọn. Giờ sẽ được kiểm tra lại khi đặt lịch.',
  // InterviewItem
  'Interview {action}; email sent.': 'Đã {action} buổi phỏng vấn; đã gửi email.',
  'Interview {action}, but the email failed: {error}': 'Đã {action} buổi phỏng vấn, nhưng gửi email lỗi: {error}',
  cancelled: 'huỷ', rescheduled: 'đổi lịch',
  'Cancel the interview on {when}? Both attendees get a cancellation email.':
    'Huỷ buổi phỏng vấn lúc {when}? Cả hai bên sẽ nhận email huỷ.',
  Reschedule: 'Đổi lịch', Feedback: 'Đánh giá', 'Google Meet': 'Google Meet',
  // api.ts labels
  Scheduled: 'Đã lên lịch', Done: 'Đã phỏng vấn', 'No-show': 'Vắng mặt', Cancelled: 'Đã huỷ',
  Hire: 'Tuyển', Maybe: 'Cân nhắc', 'No hire': 'Không tuyển',
  'No answer yet': 'Chưa phản hồi', 'Candidate accepted': 'Ứng viên đã nhận', 'Candidate declined': 'Ứng viên từ chối',
  // FeedbackDialog
  'Interview feedback': 'Đánh giá phỏng vấn', Outcome: 'Kết quả', Score: 'Điểm', Recommendation: 'Đề xuất',
  Notes: 'Ghi chú',
  // InterviewsPage
  'No interviews.': 'Chưa có buổi phỏng vấn nào.', When: 'Thời gian', Candidate: 'Ứng viên', Job: 'Vị trí',
  Where: 'Địa điểm', Status: 'Trạng thái', 'until {time}': 'đến {time}', Join: 'Tham gia',
  // UsersPage / UserDialog
  'New user': 'Người dùng mới', Role: 'Vai trò', you: 'bạn', Active: 'Đang hoạt động', Inactive: 'Ngừng hoạt động',
  'Edit {email}': 'Sửa {email}', 'New password (leave empty to keep)': 'Mật khẩu mới (để trống nếu giữ nguyên)',
  'Initial password': 'Mật khẩu ban đầu', Create: 'Tạo',
  // MailTemplatesPage
  'Delete "{name}"?': 'Xoá "{name}"?', 'New template': 'Mẫu mới',
  'Placeholders: {name} (applicant), {job} (job title), {company}. A template with a stage is offered when an applicant is moved into that stage.':
    'Biến thay thế: {name} (ứng viên), {job} (vị trí), {company}. Mẫu gắn giai đoạn sẽ được gợi ý khi chuyển ứng viên sang giai đoạn đó.',
  Subject: 'Tiêu đề', 'built-in': 'mặc định', 'Edit {name}': 'Sửa {name}',
  'Offer when moved to stage': 'Gợi ý khi chuyển sang giai đoạn', None: 'Không', Body: 'Nội dung',
} satisfies Record<string, string>
