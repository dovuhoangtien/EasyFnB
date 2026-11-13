# ADR-0009: Cảnh báo ngân sách và uptime thay vì giới hạn cứng

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Phí cố định đáng kể nhất là instance luôn bật với CPU luôn cấp (ADR-0001): `HUONG_DAN.md` ước tính 2–3 USD/ngày. Gemini tính theo lượt, chưa đo. Nhóm chạy bằng credit sự kiện hoặc gói dùng thử, nên một khoản phí bất ngờ rất dễ xảy ra nếu quên tắt. Một instance chết lúc demo cần được biết sớm.

## Quyết định

- **Budget** (`google_billing_budget`, tùy chọn khi có `billing_account`): mặc định 100 USD/tháng, cảnh báo tại 50%, 90%, 100%. Chỉ gửi thông báo.
- **Uptime check + alert policy** (khi có `alert_email`): gọi `/api/health` mỗi 5 phút qua HTTPS, báo email khi thất bại liên tục ~5 phút. `/api/health` không đụng tới AI hay ổ đĩa nên chỉ phản ánh tiến trình còn sống.
- **Công tắc chi phí:** `min_instances` (1 khi demo, 0 sau đó) và `terraform destroy`.

## Hệ quả

- Budget **không tự tắt** dịch vụ; ngân sách bị vượt thì chỉ có email. Muốn tự cắt cần Pub/Sub + hàm tắt billing, không làm vì rủi ro tắt nhầm lúc demo.
- Budget có độ trễ báo cáo (hàng giờ). Không phải bảo vệ theo thời gian thực.
- Uptime check chỉ biết service sống, không biết camera có đang gửi dữ liệu hay Gemini có hoạt động. Cái đó xem ở trang Cài đặt > Kết nối.
- Budget cần quyền `billing.budgets.create` trên billing account và API `billingbudgets`; nếu người chạy Terraform không có thì để `billing_account` trống và tạo budget trong Console.
- Hiện không có dashboard hay log-based metric riêng; xem log trong Cloud Logging là đủ cho demo.

## Phương án đã cân nhắc

- **Tự động tắt billing khi vượt ngân sách:** an toàn về tiền nhưng có thể làm sập demo.
- **Hạn chế bằng `max_instance_count` và hạn mức Gemini:** `max = 1` đã có (ADR-0003). Hạn mức Gemini đặt ở phía Google AI Studio, ngoài Terraform.
- **Không giám sát:** đơn giản nhất, nhưng chết lặng thì không ai biết.
