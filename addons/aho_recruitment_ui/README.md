# Recruitment UI — bàn giao cho team

Module `aho_recruitment_ui` cung cấp giao diện sáng cho Odoo Recruitment: ba mục điều hướng, sidebar thu gọn, card tuyển dụng, card/list ứng viên và lịch sử phỏng vấn AI trong hồ sơ. Baseline main: `f444ec8`. Bản đồng bộ token/component theo kit Figma đã được kiểm tra lại trên Odoo ngày 31/10/2026; xem phạm vi runtime bên dưới.

## Cài vào database thử

Tại thư mục repo có `docker-compose.yml`, khởi động PostgreSQL và build image:

```sh
docker compose up -d db
docker compose build odoo
```

Cài module vào database mới `hkt_ui_demo`:

```sh
docker compose run --rm --no-deps -T odoo \
  --db_host=db --db_user=odoo --db_password=odoo \
  -d hkt_ui_demo -i aho_recruitment_ui --without-demo=all \
  --stop-after-init --no-http --max-cron-threads=0
```

Sau khi cài, chạy server cho đúng database:

```sh
docker compose run --rm --no-deps --service-ports odoo \
  --db_host=db --db_user=odoo --db_password=odoo \
  -d hkt_ui_demo --db-filter='^hkt_ui_demo$'
```

Mở [trang tuyển dụng](http://localhost:8070/odoo/recruitment). Lệnh có `--service-ports` cần cổng 8070 chưa được một Odoo khác sử dụng. Khi một service Odoo đang chạy đúng database, chỉ cần nâng cấp module bằng `docker compose exec -T odoo odoo ... -u aho_recruitment_ui --stop-after-init --no-http`, với cùng các tham số kết nối DB phía trên, rồi tải lại trang.

Đây là lệnh cho database thuộc main mới, có `hr_recruitment`, `rag_interview_agent`, `rag_filter_agent`. Database cũ còn cài `t10_ai_interview` cần phương án migration riêng vì main đã xóa addon đó; không dùng hướng dẫn này như một migration dữ liệu cũ.

## Điểm nối với hub AI của teammate

| Thành phần | File / định danh ổn định | Cách nối |
| --- | --- | --- |
| Trang tuyển dụng | `views/recruitment.xml`, kế thừa `hr_recruitment.view_hr_job_kanban` | Hiện vẫn dùng luồng tạo vị trí mặc định `hr.action_create_job_position`. Team thay điểm mở tạo vị trí bằng hub thật khi đã có. |
| Dữ liệu vị trí | Model `hr.job` | Giữ ID vị trí xuyên suốt từ hub đến ứng viên. Tên, mô tả, recruiter, phòng ban và chỉ tiêu vẫn là trường Odoo hiện có. |
| Ứng viên theo vị trí | `hr_recruitment.action_hr_job_applications` | UI đổi tên và gắn bảng kế thừa; giữ đủ view mode, filter và `default_job_id` của core. |
| Tất cả ứng viên | `aho_recruitment_ui.action_applicant_tracking` | Ưu tiên list/card; giữ thêm graph/calendar/pivot/activity, quyền Odoo và bộ lọc core; không hardcode ID database. |
| Tóm tắt trên card | `models/applicant.py` | Hai trường tính toán `aho_interview_state`, `aho_next_action` chỉ phản ánh phiên RAG mới nhất và HR phụ trách; không phải trạng thái scheduler hay toàn bộ ATS pipeline. |
| Lịch sử AI | `views/applicant.xml`, quan hệ `rag_interview_ids` | Mở phiên/report của `rag_interview_agent`; điểm hiển thị là tham khảo, người tuyển xem bằng chứng. |
| Màu / khoảng cách | `static/src/css/design_system.css` (token theo kit Venture CRM), `workspace_components.scss` (nút, badge, card, bảng, header) | Chỉ dùng biến `--aho-*`; không khai báo lại style component ở file khác. Sidebar ở `material_sidebar.scss`. |

Quy trình tuyển dụng dùng chung theo lĩnh vực, phiên bản yêu cầu và quyền agent đọc nguồn đó chưa được module UI này triển khai. Cần thống nhất model/schema với phần backend trước khi thêm màn hình quản lý. Talent Pool metadata-only cũng chưa được bảo vệ bởi module này; việc ẩn menu không thay quyền truy cập dữ liệu.

## Kiểm tra sau khi tích hợp

Trạng thái `ready` chỉ xác nhận đã tạo link; không dùng nhãn “Đã gửi” vì backend chưa cung cấp bằng chứng gửi thư mời. Icon dùng `.oi` + `data-icon` của Odoo 20; Font Awesome không có trong runtime đã kiểm tra.

1. Với hai vị trí và hồ sơ giả khác nhau, mở **Xem ứng viên** ở từng card: hồ sơ thuộc đúng vị trí, đổi card/list giữ bộ lọc.
2. Mở **New** từ vị trí: vị trí tuyển dụng được điền đúng; đóng nháp khi không lưu. Luồng tạo đợt tuyển qua hub cần được kiểm tra riêng khi team nối xong.
3. Kéo một card thử giữa hai giai đoạn rồi trả lại; mở profile, lịch sử AI và báo cáo vẫn được.
4. Sidebar có ba nhóm: Tuyển dụng (Vị trí, Ứng viên), Công cụ AI (Phỏng vấn tự động, Chấm CV nhanh: công cụ độc lập, chưa gắn vào hồ sơ) và Thiết lập (Phòng ban, Quy trình tuyển dụng, Lý do từ chối, Thông tin công ty cho AI, Cài đặt; mục hiện theo quyền). Thu gọn còn icon 64px và mở lại được. Kiểm tra desktop và cửa sổ hẹp; không tràn trang, không mất điều hướng.
5. Bảng/search kế thừa primary từ Odoo: giữ đủ trường tùy chọn, multi-edit, ba thao tác header và bộ lọc core. Kiểm tra lại các view Calendar/Graph/Pivot/Activity; Calendar ở đây hiển thị hạn công việc, không phải bằng chứng đã có AI scheduling.
6. Kiểm thử riêng scheduling, email, voice, provider và publishing bằng luồng tích hợp thật. Kết quả UI không chứng minh các thao tác đó thành công.

## Bằng chứng hiện có và giới hạn

Đã cài/nâng cấp trên Odoo `20.0-20261015`, dùng OrbStack, PostgreSQL 16. Lượt kiểm tra 31/10/2026 đã cài vào DB mới `hkt_ui_install_check` trong image hiện tại: `aho_recruitment_ui`, `rag_interview_agent`, `rag_filter_agent` đều ở trạng thái `installed`; không cấu hình API key cho tiến trình cài thử. Bản token/component Figma đã nâng cấp thành công trên `hkt_ux_main_test`; sửa lỗi template nhóm Thiết lập, icon, cột Kanban và header khi chạy thật. Kiểm tra sáu trường hợp của Việc tiếp theo bằng record thử trong bộ nhớ, gồm stage đã tuyển và archived; không thay đổi stage hoặc gọi provider trong bài kiểm tra này. Đã kiểm tra các thao tác UI trên dữ liệu `[UX TEST]`, gồm kéo Kanban, filter, default vị trí, profile/report và viewport 390/768/1280px. Các báo cáo fixture ghi rõ là dữ liệu giả; không dùng làm kết quả AI hoặc ROI trong bài nộp.

Đã so diff với main `f444ec8`: addon UI không sửa source `hr_recruitment`, `rag_interview_agent` hoặc `rag_filter_agent`, nhưng có kế thừa view/action làm thay đổi trải nghiệm. Audit đã phát hiện và khôi phục các khả năng core từng bị thu hẹp: 34 trường list gốc, 34 bộ lọc gốc, 3 thao tác header, multi-edit và 7 view mode. Việc so source backend không thay thế kiểm tra view/action.

Main đã xóa `t10_ai_interview` và ML tại `e11da0a`; UI này không khôi phục scheduler, luật AI theo vị trí, kết quả CV gắn applicant, quyết định AI/human riêng hoặc playbook/agent log của addon cũ. Core vẫn có họp thủ công, stage/refuse/hired, ghi chú và Talent Pool. `hr.recruitment.stage` đã có `requirements`, `job_ids`, `template_id`; agent RAG hiện chưa đọc các yêu cầu giai đoạn này. Company background ở `res.company.rag_background` có thể chỉnh theo quyền company; quyền HR manager không tự tương đương quyền quản trị company/API keys.

Dockerfile của main dùng `odoo:latest`. Kiểm tra database mới trong image hiện tại không chứng minh chạy lại thành công trên một image khác hoặc máy sạch. Chốt version/runtime và commit demo trước khi ghi vào PDF cuối.

## Khi cần quay lại bản trước

Giữ bản sao database trước khi tích hợp. Nếu chỉ chỉnh giao diện, quay lại commit UI đã kiểm tra, nâng cấp `aho_recruitment_ui` và tải lại assets. Nếu đổi model/schema/backend, dùng phương án migration/khôi phục DB của team; không xóa database hoặc gỡ addon AI để xử lý lỗi giao diện.
