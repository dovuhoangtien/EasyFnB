# ADR-0001: Một service Cloud Run chạy cả web và API

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Máy chủ là một ứng dụng FastAPI (`easy-fnb/server`) phục vụ luôn bản React đã build (`dist/`) qua route `/{path:path}`. Nó giữ kết nối SSE, WebSocket và MJPEG lâu, và có một vòng nền (`hub.tick_forever`) chuyển việc theo thời gian. `Dockerfile` hai tầng đã có sẵn và được viết cho Cloud Run (đọc `PORT`, nhận biết `K_SERVICE`). Nhóm 2–3 người, demo ngày 14/11, đề tài đăng ký nêu rõ "Cloud Run".

## Quyết định

Triển khai **một service Cloud Run** `easy-fnb` ở `asia-southeast1`, gen2, 1 vCPU, 1 GiB, CPU luôn cấp (`cpu_idle = false`), `timeout = 3600s`, `max_instance_request_concurrency = 200`. Web và API cùng một container, cùng một origin.

## Hệ quả

- Triển khai và quay lui đơn giản: một image, một lệnh.
- Không cần CORS thật sự hay CDN riêng cho web.
- `cpu_idle = false` là bắt buộc để vòng chuyển việc chạy khi không có request; đó cũng là khoản tốn tiền chính (ADR-0009).
- 1 GiB thay vì 512 MiB trong `HUONG_DAN.md` vì `google-adk` nạp nhiều thư viện. **Chưa đo** mức RAM thực; nếu đo thấy dưới ~400 MiB có thể hạ xuống.
- Concurrency 200 vì mỗi trang đang mở giữ một kết nối SSE; mặc định 80 dễ chạm trần khi có nhiều điện thoại và camera. Con số 200 là ước lượng, chưa thử tải.
- Timeout tối đa của Cloud Run là 60 phút; client phải tự nối lại SSE (trình duyệt đã làm vậy theo `HUONG_DAN.md`).

## Phương án đã cân nhắc

- **Tách web lên Firebase Hosting / Cloud Storage + CDN:** thêm một thành phần, thêm CORS, không có lợi cho demo.
- **GKE / Compute Engine:** quản lý nhiều hơn, không cần cho một tiến trình.
- **Cloud Run Functions:** không hợp với kết nối lâu và vòng nền.
- **Cloud Run có GPU (L4):** báo cáo tính ~$242/tháng cho 12 giờ/ngày, trong khi AI nhìn đã chạy ở quán (ADR-0002).
