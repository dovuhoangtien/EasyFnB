# ADR-0002: AI nhìn chạy tại quán, cloud chỉ nhận sự kiện

- Trạng thái: Đề xuất. **Thay thế một phần bởi ADR-0010** cho kiến trúc đích (suy luận lên cloud). Vẫn đúng cho demo hiện tại và cho chế độ edge (chế độ C).
- Ngày: 2026-11-13

## Bối cảnh

Pipeline thị giác (`vision-test`: YOLO26, RTMPose, PE-Core, TensorRT) cần GPU và đọc video liên tục. Nó đang chạy trên laptop RTX 3050 4 GB, nhanh nhất ~57 khung/giây. Đẩy video thô lên cloud tốn băng thông, tiền GPU, và đưa hình ảnh khách ra ngoài quán. Pipeline đã có đường gửi lên máy chủ: sự kiện, ảnh cắt, khung trực tiếp, trạng thái bàn (`/api/edge/*`), và đã làm mờ mặt trước khi ảnh rời máy.

## Quyết định

Toàn bộ suy luận thị giác chạy **tại quán** (edge). Cloud Run chỉ nhận **sự kiện nhỏ và ảnh cắt đã làm mờ mặt**, điều phối việc và gọi Gemini để xác minh/tóm tắt. Không dùng GPU trên Google Cloud.

## Hệ quả

- Chi phí cloud gần như cố định, không tăng theo số camera (báo cáo ước tính 70–75% chi phí là phần cố định).
- Quán phải có một máy chạy pipeline; engine TensorRT gắn với GPU đã build ra nó (`HUONG_DAN.md`).
- Mất mạng thì pipeline vẫn nhìn được nhưng nhân viên không nhận việc, vì điều phối nằm trên cloud. **Chưa xử lý, chưa kiểm tra** camera làm gì khi máy chủ không nhận. Báo cáo đề xuất đưa hub về LAN ở quán thật; ngoài phạm vi demo.
- Mặt khách không rời quán ở dạng rõ, giúp giảm rủi ro dữ liệu (không thay thế đánh giá pháp lý).
- Chuỗi tin cậy: camera ↔ máy chủ chỉ được bảo vệ bằng `EDGE_KEY` (ADR-0007).

## Phương án đã cân nhắc

- **Đẩy video lên cloud, chạy GPU L4 trên Cloud Run hoặc GCE:** đắt, cần 2–4 Mbps mỗi camera, hình ảnh rời quán.
- **Cho Gemini nhìn mỗi camera 5 giây một lần:** báo cáo ước tính ~$435/tháng cho 8 camera.
- **Chạy cả điều phối ở LAN:** đúng hướng cho sản phẩm thật nhưng là bài làm riêng.
