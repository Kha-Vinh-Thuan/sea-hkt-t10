# Recruitment UI — bàn giao cho team

Module `aho_recruitment_ui` cung cấp giao diện sáng cho Odoo Recruitment: ba mục điều hướng, sidebar thu gọn, card tuyển dụng, card/list ứng viên và lịch sử phỏng vấn AI trong hồ sơ. Mã UI đã kiểm tra tại commit `5534eef`, dựa trên main `f444ec8`.

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
| Ứng viên theo vị trí | `hr_recruitment.action_hr_job_applications` | UI chỉ đổi tên/chế độ xem và gắn cùng list view; giữ nguyên filter và `default_job_id` của core. |
| Tất cả ứng viên | `aho_recruitment_ui.action_applicant_tracking` | List/card/form; giữ quyền truy cập của Odoo, không hardcode ID database. |
| Tóm tắt trên card | `models/applicant.py` | Hai trường tính toán `aho_interview_state`, `aho_next_action` chỉ phản ánh phiên RAG mới nhất và HR phụ trách; không phải trạng thái scheduler hay toàn bộ ATS pipeline. |
| Lịch sử AI | `views/applicant.xml`, quan hệ `rag_interview_ids` | Mở phiên/report của `rag_interview_agent`; điểm hiển thị là tham khảo, người tuyển xem bằng chứng. |
| Màu / khoảng cách | `static/src/css/design_system.css`, `workspace_components.scss` | Dùng các biến `--aho-*` cho thành phần hub để thống nhất nhận diện. Sidebar ở `material_sidebar.scss`. |

Quy trình tuyển dụng dùng chung theo lĩnh vực, phiên bản yêu cầu và quyền agent đọc nguồn đó chưa được module UI này triển khai. Cần thống nhất model/schema với phần backend trước khi thêm màn hình quản lý. Talent Pool metadata-only cũng chưa được bảo vệ bởi module này; việc ẩn menu không thay quyền truy cập dữ liệu.

## Kiểm tra sau khi tích hợp

1. Với hai vị trí và hồ sơ giả khác nhau, mở **Xem ứng viên** ở từng card: hồ sơ thuộc đúng vị trí, đổi card/list giữ bộ lọc.
2. Mở **New** từ vị trí: vị trí tuyển dụng được điền đúng; đóng nháp khi không lưu. Luồng tạo đợt tuyển qua hub cần được kiểm tra riêng khi team nối xong.
3. Kéo một card thử giữa hai giai đoạn rồi trả lại; mở profile, lịch sử AI và báo cáo vẫn được.
4. Sidebar chỉ ba mục; thu gọn/mở lại được. Kiểm tra desktop và cửa sổ hẹp; không tràn trang, không mất điều hướng.
5. Kiểm thử riêng scheduling, email, voice, provider và publishing bằng luồng tích hợp thật. Kết quả UI không chứng minh các thao tác đó thành công.

## Bằng chứng hiện có và giới hạn

Đã cài/nâng cấp trên Odoo `20.0-20261015`, dùng OrbStack, PostgreSQL 16. Lượt kiểm tra 31/10/2026 đã cài vào DB mới `hkt_ui_install_check` trong image hiện tại: `aho_recruitment_ui`, `rag_interview_agent`, `rag_filter_agent` đều ở trạng thái `installed`; không cấu hình API key cho tiến trình cài thử. Đã kiểm tra các thao tác UI trên dữ liệu `[UX TEST]`, gồm kéo Kanban, filter, default vị trí, profile/report và viewport 390/768/1280px. Các báo cáo fixture ghi rõ là dữ liệu giả; không dùng làm kết quả AI hoặc ROI trong bài nộp.

Dockerfile của main dùng `odoo:latest`. Kiểm tra database mới trong image hiện tại không chứng minh chạy lại thành công trên một image khác hoặc máy sạch. Chốt version/runtime và commit demo trước khi ghi vào PDF cuối.

## Khi cần quay lại bản trước

Giữ bản sao database trước khi tích hợp. Nếu chỉ chỉnh giao diện, quay lại commit UI đã kiểm tra, nâng cấp `aho_recruitment_ui` và tải lại assets. Nếu đổi model/schema/backend, dùng phương án migration/khôi phục DB của team; không xóa database hoặc gỡ addon AI để xử lý lỗi giao diện.
