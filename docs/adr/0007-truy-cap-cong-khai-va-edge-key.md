# ADR-0007: Mở công khai, chỉ camera có khoá; rủi ro được chấp nhận tạm

- Trạng thái: Đề xuất (có rủi ro mở, cần người duyệt chấp nhận)
- Ngày: 2026-11-13

## Bối cảnh

Điện thoại nhân viên và máy camera không có tài khoản Google, nên Cloud Run phải nhận request ẩn danh (`allUsers` có `roles/run.invoker`). Đọc `server/app.py`: chỉ bốn endpoint `/api/edge/event|evidence|frame|tables` có `Depends(edge_auth)` (kiểm `X-Edge-Key`). **Mọi endpoint còn lại không kiểm tra gì**, gồm:

| Endpoint | Hậu quả nếu bị gọi bởi người lạ |
|---|---|
| `POST /api/reset` | Xoá ca đang chạy |
| `PUT /api/zones`, `/api/staff`, `/api/settings` | Đổi vùng bàn, nhân viên, cài đặt (có thể tắt kiểm tra) |
| `POST /api/alerts`, `/ack`, `/done`, `/cancel`, `/assign` | Tạo hoặc đóng việc giả |
| `POST /api/assistant`, `/api/report/summary`, `/api/ai/test` | Tiêu quota và tiền Gemini |
| `GET /api/state`, `/api/camera/*`, `/api/crops/*`, `/api/stream` | Xem trạng thái, ảnh cắt, hình camera trực tiếp |
| `POST /api/phone/{cam}/frame`, WebSocket `/api/phone/{cam}/ws` | Đẩy khung hình giả vào luồng camera điện thoại |

CORS cũng mở `*`.

## Quyết định

Cho demo, **chấp nhận** việc mở công khai, với các biện pháp giảm nhẹ nằm trong IaC:

1. `EDGE_KEY` ngẫu nhiên 40 ký tự bắt buộc cho 4 endpoint của camera (ADR-0005).
2. `max_instance_count = 1`: giới hạn thiệt hại về tiền Cloud Run.
3. Cảnh báo ngân sách (ADR-0009).
4. URL `*.run.app` không công bố; chỉ đưa cho người cần dùng, và gỡ service (`terraform destroy`) hoặc `min_instances = 0` sau demo.
5. `allow_unauthenticated` là biến: đặt `false` thì cần đặt proxy hoặc IAP phía trước (điện thoại sẽ không vào được nếu không có thêm gì).

**Chưa quyết, cần làm trước khi dùng cho quán thật:** mã thông báo cho chủ quán (đổi/đọc/AI) và liên kết riêng cho nhân viên, siết CORS. Đây là thay đổi code, nằm ngoài phạm vi IaC này.

## Hệ quả

- Rủi ro lớn nhất khi demo là ai đó vô tình hoặc cố ý bấm `reset` giữa buổi trình diễn, hoặc đốt quota Gemini. Không có biện pháp kỹ thuật nào ngăn điều đó ngoài việc giữ URL kín.
- **Không nên đưa URL vào video dự thi hoặc slide công khai** nếu chưa có xác thực.
- Ảnh cắt đã làm mờ mặt, nhưng bằng chứng và hình trực tiếp vẫn thuộc về quán; không dùng footage thật của quán trên bản này.

## Phương án đã cân nhắc

- **IAP trước Cloud Run (cần load balancer + domain):** đúng cho sản phẩm; quá nặng cho demo.
- **Cloud Run IAM (cần đăng nhập Google):** điện thoại nhân viên và camera không dùng được nếu không thêm lớp token.
- **Cloud Armor giới hạn IP:** IP quán và IP điện thoại đổi liên tục.
- **Thêm middleware token vào `app.py` ngay:** là cách sửa đúng nhất, nhưng làm thay đổi hợp đồng API (`server/API.md`) và frontend; để việc sau.
