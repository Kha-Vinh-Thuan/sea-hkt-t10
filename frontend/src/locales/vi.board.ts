// Vietnamese texts for the board screens; key = the English text passed to t().
export default {
  // board + job list
  'Job positions': 'Vị trí tuyển dụng', 'New job': 'Thêm vị trí', 'Edit job': 'Sửa vị trí', Open: 'Đang mở', Closed: 'Đã đóng',
  '{hired} / {openings} hired': 'Đã tuyển {hired} / {openings}', 'No archived applicants.': 'Không có ứng viên đã lưu trữ.',
  'Interview booked': 'Đã đặt lịch phỏng vấn', 'No interview booked yet': 'Chưa đặt lịch phỏng vấn',
  '{days}d in stage': '{days} ngày ở giai đoạn này', 'Drop applicants here': 'Thả ứng viên vào đây',
  // filters
  'Search name, email, CV, tags': 'Tìm tên, email, CV, thẻ', 'Search applicants': 'Tìm ứng viên', 'Min priority': 'Ưu tiên tối thiểu',
  Any: 'Tất cả', Tag: 'Thẻ', Mine: 'Của tôi', 'Show archived': 'Hiện đã lưu trữ',
  // job dialog
  'Edit job position': 'Sửa vị trí tuyển dụng', 'New job position': 'Vị trí tuyển dụng mới', Title: 'Tiêu đề', Location: 'Địa điểm',
  'Employment type': 'Hình thức làm việc', Remote: 'Từ xa', Description: 'Mô tả', Requirements: 'Yêu cầu',
  'One per line': 'Mỗi dòng một ý', 'Expected degree': 'Bằng cấp mong muốn',
  'e.g. Bachelor in Computer Science': 'VD: Cử nhân Khoa học máy tính',
  'Salary from (VND / month)': 'Lương từ (VND / tháng)', 'Salary to (VND / month)': 'Lương đến (VND / tháng)',
  'Opens on': 'Ngày mở', 'Closes on': 'Ngày đóng', 'Interview length (min)': 'Thời lượng phỏng vấn (phút)',
  Openings: 'Số lượng cần tuyển', 'Hiring manager': 'Quản lý tuyển dụng', None: 'Không có', Interviewers: 'Người phỏng vấn',
  'Offered first when booking an interview for this job': 'Được gợi ý trước khi đặt lịch phỏng vấn cho vị trí này',
  'Published on careers site': 'Đăng trên trang tuyển dụng', Create: 'Tạo',
  // applicant page
  'Back to board': 'Quay lại bảng', 'Stuck in this stage': 'Bị kẹt ở giai đoạn này', Next: 'Tiếp theo', Overdue: 'Quá hạn',
  Due: 'Hạn', 'Schedule interview': 'Đặt lịch phỏng vấn', 'Send email': 'Gửi email', 'Copy to job': 'Sao chép sang vị trí khác',
  Archive: 'Lưu trữ', Restore: 'Khôi phục', Refuse: 'Từ chối',
  'In this stage for {days} days (since {when})': 'Ở giai đoạn này {days} ngày (từ {when})',
  'A reminder only; it does not block moving the card.': 'Chỉ là lời nhắc, không chặn việc chuyển thẻ.',
  'To move on': 'Để chuyển tiếp', 'Archived: hidden from the board.': 'Đã lưu trữ: ẩn khỏi bảng.', Refused: 'Đã từ chối',
  Schedule: 'Đặt lịch', 'No interviews yet.': 'Chưa có buổi phỏng vấn.', 'CV text': 'Nội dung CV',
  'No text could be extracted from this CV.': 'Không trích xuất được nội dung từ CV này.', Activity: 'Hoạt động',
  'Recruiter notes': 'Ghi chú tuyển dụng', 'Saved.': 'Đã lưu.',
  'Applicant refused and emailed.': 'Đã từ chối ứng viên và gửi email.', 'Applicant refused.': 'Đã từ chối ứng viên.',
  'Applicant refused, but the email failed: {error}': 'Đã từ chối ứng viên, nhưng gửi email lỗi: {error}',
  'Copied to {job}.': 'Đã sao chép sang {job}.', 'Email sent.': 'Đã gửi email.', 'Email not sent: {error}': 'Chưa gửi được email: {error}',
  'Times proposed': 'Đã đề xuất khung giờ', '{what} and emailed to the candidate.': '{what} và đã gửi email cho ứng viên.',
  '{what}, but the email failed: {error}': '{what}, nhưng gửi email lỗi: {error}',
  // applicant fields
  Nobody: 'Không ai', 'Inactive user #{id}': 'Người dùng ngừng hoạt động #{id}', Priority: 'Ưu tiên', Tags: 'Thẻ',
  'Type and press Enter': 'Gõ rồi nhấn Enter', 'Next step': 'Bước tiếp theo', 'e.g. Call about salary': 'VD: Gọi trao đổi lương',
  'Next step by': 'Người làm bước tiếp', 'Recruiter (owner)': 'Tuyển dụng viên (phụ trách)', 'Source detail': 'Chi tiết nguồn',
  'e.g. referrer name': 'VD: tên người giới thiệu', Degree: 'Bằng cấp', 'Available from': 'Có thể bắt đầu từ',
  'Expected salary': 'Lương mong muốn', 'Proposed salary': 'Lương đề xuất', 'Saving…': 'Đang lưu…',
  // attachments, pools, other applications
  Attachments: 'Tệp đính kèm', Upload: 'Tải lên', 'PDF, DOCX, TXT, PNG or JPG, up to 5 MB.': 'PDF, DOCX, TXT, PNG hoặc JPG, tối đa 5 MB.',
  'Delete {name}': 'Xoá {name}', 'Delete {name}?': 'Xoá {name}?', 'Pool: {name}': 'Kho: {name}', 'Add to pool': 'Thêm vào kho',
  'Also applied to': 'Cũng ứng tuyển vào', archived: 'đã lưu trữ', closed: 'đã đóng',
  // dialogs
  'Refuse applicant': 'Từ chối ứng viên', Reason: 'Lý do', 'Send refusal email to the candidate': 'Gửi email từ chối cho ứng viên',
  'Copy {name} to another job': 'Sao chép {name} sang vị trí khác', Job: 'Vị trí', Copy: 'Sao chép',
  Template: 'Mẫu', Subject: 'Tiêu đề', Body: 'Nội dung', Send: 'Gửi',
  // reports
  'No jobs yet.': 'Chưa có vị trí nào.', 'Hiring progress': 'Tiến độ tuyển dụng', Applicants: 'Ứng viên',
  'Hired / openings': 'Đã tuyển / cần tuyển', 'Avg days to hire': 'Số ngày tuyển TB', 'Applicants by stage': 'Ứng viên theo giai đoạn',
  'Applicants by source': 'Ứng viên theo nguồn', 'Refused by reason': 'Từ chối theo lý do',
  // talent pools
  'Delete the pool "{name}"? Its applicants are kept.': 'Xoá kho "{name}"? Ứng viên trong kho vẫn được giữ.',
  'No pools yet.': 'Chưa có kho nào.', 'New pool name': 'Tên kho mới', 'Create pool': 'Tạo kho',
  'Select a pool to see its applicants.': 'Chọn một kho để xem ứng viên.',
  'No applicants yet. Add them from the applicant panel.': 'Chưa có ứng viên. Thêm từ trang ứng viên.', Remove: 'Gỡ',
  'More details': 'Thêm chi tiết', 'Fewer details': 'Thu gọn', 'Show email': 'Xem nội dung email', 'Hide email': 'Ẩn nội dung email',
} satisfies Record<string, string>
