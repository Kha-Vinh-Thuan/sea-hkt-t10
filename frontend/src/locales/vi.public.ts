// Vietnamese texts for the public screens; key = the English text passed to t().
export default {
  // login
  'Sign in': 'Đăng nhập', Password: 'Mật khẩu',
  // careers site
  'Join our team': 'Gia nhập đội ngũ', 'Find a role where you can do your best work.': 'Tìm vị trí để bạn phát huy hết khả năng.',
  'All jobs': 'Tất cả việc làm', 'No open positions right now.': 'Hiện chưa có vị trí nào đang tuyển.',
  Any: 'Tất cả', Location: 'Địa điểm', 'Employment type': 'Hình thức làm việc', Remote: 'Từ xa', 'On-site': 'Tại văn phòng',
  'Clear filters': 'Xoá bộ lọc', 'No jobs match these filters.': 'Không có việc làm phù hợp với bộ lọc.',
  'From {amount} VND': 'Từ {amount} VND', 'Up to {amount} VND': 'Đến {amount} VND',
  'Salary:': 'Lương:', '{salary} / month': '{salary} / tháng', 'Degree:': 'Bằng cấp:', 'Apply by:': 'Hạn nộp:',
  'About the role': 'Về vị trí', Requirements: 'Yêu cầu', 'Apply for this job': 'Ứng tuyển vị trí này',
  // apply form
  'Please attach your CV.': 'Vui lòng đính kèm CV.', 'CV must be {mb} MB or smaller.': 'CV tối đa {mb} MB.',
  'Thanks! Your application was received. We will contact you by email.':
    'Cảm ơn bạn! Chúng tôi đã nhận hồ sơ và sẽ liên hệ qua email.',
  'Full name': 'Họ và tên', 'LinkedIn profile': 'Hồ sơ LinkedIn', 'Short introduction': 'Giới thiệu ngắn',
  'Change CV': 'Đổi CV', 'Upload CV': 'Tải CV lên', 'PDF, DOCX or TXT, up to {mb} MB': 'PDF, DOCX hoặc TXT, tối đa {mb} MB',
  'Submitting…': 'Đang gửi…', 'Submit application': 'Gửi hồ sơ',
  // booking + interview answer pages
  'Interview for {job}': 'Phỏng vấn vị trí {job}', 'Book your interview on {when}?': 'Đặt lịch phỏng vấn vào {when}?',
  'Your interview is booked for {when}.': 'Đã đặt lịch phỏng vấn vào {when}.',
  'A calendar invitation is on its way to your inbox.': 'Lời mời trên lịch đang được gửi tới hộp thư của bạn.',
  'Hello {name}, please pick a time that suits you ({minutes} minutes{location}).':
    'Chào {name}, vui lòng chọn thời gian phù hợp ({minutes} phút{location}).',
  'None of the proposed times is available any more. Please reply to the recruiter.':
    'Các khung giờ đề xuất đều đã hết. Vui lòng phản hồi lại nhà tuyển dụng.',
  "Times are shown in your browser's time zone.": 'Thời gian hiển thị theo múi giờ của trình duyệt.',
  'Hello {name}, your interview is on {when}.': 'Chào {name}, buổi phỏng vấn của bạn vào {when}.',
  'Join with Google Meet': 'Tham gia qua Google Meet', 'This interview has been cancelled.': 'Buổi phỏng vấn này đã bị huỷ.',
  'Your answer: accepted. Thank you!': 'Bạn đã xác nhận tham gia. Cảm ơn bạn!',
  'Your answer: declined. Thank you!': 'Bạn đã từ chối tham gia. Cảm ơn bạn!',
  'I will attend': 'Tôi sẽ tham gia', 'I cannot attend': 'Tôi không thể tham gia',
  // Google Calendar connect result (App.tsx)
  'Google Calendar connected.': 'Đã kết nối Google Calendar.',
  'Google Calendar was not connected (access denied).': 'Chưa kết nối Google Calendar (bị từ chối quyền truy cập).',
  'Google Calendar could not be connected, please try again.': 'Không kết nối được Google Calendar, vui lòng thử lại.',
} satisfies Record<string, string>
