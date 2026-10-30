// Vietnamese texts shared by every staff screen (navbar, labels from api.ts, generic words); key = the English text.
export default {
  // navbar
  Pipeline: 'Tuyển dụng', Interviews: 'Phỏng vấn', More: 'Thêm', Reports: 'Báo cáo', 'Talent pools': 'Kho ứng viên',
  'Careers site': 'Trang tuyển dụng', Users: 'Người dùng', 'Email templates': 'Mẫu email', 'Account menu': 'Menu tài khoản',
  'Click to disconnect': 'Bấm để ngắt kết nối', Connected: 'Đã kết nối', 'Connect Google Calendar': 'Kết nối Google Calendar',
  'Disconnect Google Calendar? New interviews will no longer be added to it.':
    'Ngắt kết nối Google Calendar? Lịch phỏng vấn mới sẽ không được thêm vào nữa.',
  'Sign out': 'Đăng xuất', 'Light mode': 'Giao diện sáng', 'Dark mode': 'Giao diện tối',
  // roles
  Admin: 'Quản trị', Recruiter: 'Tuyển dụng viên', Interviewer: 'Người phỏng vấn',
  // stages
  New: 'Mới', Screening: 'Sàng lọc', Interview: 'Phỏng vấn', Offer: 'Đề nghị', Hired: 'Đã tuyển', Rejected: 'Từ chối',
  // sources
  LinkedIn: 'LinkedIn', Referral: 'Giới thiệu', 'Job board': 'Trang việc làm', Other: 'Khác',
  // employment types
  'Full-time': 'Toàn thời gian', 'Part-time': 'Bán thời gian', Internship: 'Thực tập', Contract: 'Hợp đồng',
  // generic
  Cancel: 'Huỷ', Save: 'Lưu', Close: 'Đóng', Delete: 'Xoá', Edit: 'Sửa', Back: 'Quay lại', Loading: 'Đang tải',
  'Loading…': 'Đang tải…', Email: 'Email', Name: 'Tên', Phone: 'Số điện thoại', Stage: 'Giai đoạn', Source: 'Nguồn',
} satisfies Record<string, string>
