# ADR-0013: Hai loại luồng, trạng thái ngoài RAM

- Trạng thái: Đề xuất (kiến trúc đích; **ngoài phạm vi IaC demo**)
- Ngày: 2026-11-13
- Thay thế một phần: ADR-0003 (ADR-0003 vẫn đúng cho demo một instance)

## Bối cảnh

Hai loại dữ liệu chảy khác bản chất:

- **Khung hình:** lượng lớn, chỉ khung mới nhất có giá trị. Demo đã làm đúng điều này: `gui_may_chu.py` chỉ giữ khung mới nhất ("mạng chậm thì bỏ khung cũ chứ không dồn ứ") và `hub.frames` chỉ giữ một khung mỗi camera.
- **Sự kiện:** lượng nhỏ, **không được mất** (nhân viên phải nhận việc). Demo dùng hàng đợi trong tiến trình (tối đa 500) và gửi HTTP; mất tiến trình là mất hàng đợi.

Và `Hub` giữ việc, bàn, nhật ký, danh sách SSE trong RAM của một tiến trình (ADR-0003), nên không chạy nhiều instance được. ~12 kết nối SSE mỗi quán đưa 1.000 quán lên ~12.000 kết nối giữ lâu.

## Quyết định

1. **Khung hình đi qua hàng "mới nhất thắng"**: mỗi camera một khe trong Redis (Memorystore), ghi đè, TTL vài giây. Không dồn ứ, không ghi đĩa.
2. **Sự kiện và ảnh bằng chứng đi qua Pub/Sub**: bền, có thử lại, khử trùng bằng `eid`, ảnh bằng chứng lưu Cloud Storage và sự kiện chỉ mang đường dẫn.
3. **Hub không giữ trạng thái trong RAM:** việc, bàn, cài đặt, nhật ký nằm ở Firestore. Hub nhiều instance; bộ đếm chuyển việc theo thời gian chạy bằng cơ chế có khoá hoặc tác vụ định kỳ, không phụ thuộc một tiến trình.
4. **Phát tán đến người dùng** qua Firestore `onSnapshot` (báo cáo đề xuất) hoặc Redis pub/sub cho lớp SSE; chọn khi đo.

## Hệ quả

- Hub co giãn ngang và sống qua khởi động lại; mất việc đang mở khi deploy không còn.
- Thêm ba dịch vụ (Redis, Pub/Sub, Firestore) cần vận hành và chi phí cố định.
- Phải viết lại `hub.py` (hiện đồng bộ, trạng thái trong RAM) và lớp SSE. Đây là việc code lớn, không phải cấu hình.
- Firestore có độ trễ ghi và đọc cao hơn RAM; bộ đếm chuyển việc (giây) chịu được, nhưng cần thử.
- Rủi ro đã biết ở demo: `hub.edge_event` và `_attach_evidence` ghi file đồng bộ trong handler async, chặn vòng lặp (nặng hơn khi `DATA_DIR` là bucket gcsfuse). Nếu giữ hub hiện tại lâu hơn, bọc các lần ghi bằng `asyncio.to_thread`.
- Firestore không có truy vấn vector có người nghe theo thời gian thực (báo cáo); không ảnh hưởng luồng này.

## Phương án đã cân nhắc

- **Giữ một instance, trạng thái trong RAM (demo):** đúng cho demo; không scale, mất dữ liệu khi khởi động lại.
- **Redis cho cả trạng thái hub:** nhanh; Memorystore là một điểm chết đơn nếu không bật nhân bản, và dữ liệu cần bền (nhật ký ca) nên Firestore hợp hơn.
- **Cloud SQL (Postgres):** quan hệ rõ ràng, nhưng kết nối giữ lâu từ nhiều instance Cloud Run cần quản lý pool; Firestore hợp hơn với `onSnapshot`.
- **Kafka (Managed):** mạnh hơn Pub/Sub nhưng thêm tiền cố định và vận hành, không cần ở quy mô này.
