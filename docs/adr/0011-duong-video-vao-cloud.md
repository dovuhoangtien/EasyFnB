# ADR-0011: Đường video vào cloud

- Trạng thái: Đề xuất (kiến trúc đích; **ngoài phạm vi IaC demo**)
- Ngày: 2026-11-13

## Bối cảnh

Camera và đầu ghi NVR nằm sau NAT của quán, nên cloud không kéo luồng về được; quán phải **đẩy lên**. Khi suy luận ở cloud (ADR-0010), thứ cần đẩy là video. Ràng buộc:

- Cloud Run chỉ nhận HTTP, gRPC và WebSocket; không nhận UDP hay TCP thô. RTSP/SRT/WebRTC cần dịch vụ chạy trên GCE hoặc GKE.
- Demo hiện có đường JPEG qua WebSocket (`/api/phone/{cam}/ws`, ~6 khung/giây, 960 px) và MJPEG ra cho pipeline. Đường này vòng đi-về qua internet nếu pipeline vẫn ở quán.
- Báo cáo đề xuất go2rtc trên máy thu ngân và luồng phụ RTSP của NVR.
- Quán chỉ có đường lên của quán; băng thông thực **chưa đo**.

## Quyết định

1. **Cổng phát luồng ở quán, không giải mã, không GPU.** go2rtc hoặc ffmpeg lấy luồng phụ RTSP của NVR và đẩy H.264 lên cloud qua TLS (đóng gói lại, không mã hoá lại). Lọc chuyển động là tùy chọn.
2. **Cổng nhận video ở cloud:** dịch vụ RTSP/SRT/WebRTC trên GCE hoặc GKE (có TCP/UDP), cộng một endpoint WebSocket JPEG trên Cloud Run cho điện thoại-camera và quán rất ít camera.
3. **Giải mã và lấy mẫu ở cloud** (NVDEC hoặc CPU), mặc định ~5 khung/giây, rồi đặt vào hàng khung (ADR-0013).
4. **Luồng phụ độ phân giải thấp**, đặt bitrate trên camera; không đẩy luồng chính.

## Hệ quả

- Ước tính băng thông (chưa đo): H.264 luồng phụ 0,3 đến 1 Mbps mỗi camera; JPEG từng khung 1,6 đến 4 Mbps mỗi camera. H.264 tốt hơn khoảng 3 đến 6 lần, nên là đường chính.
- Quán vẫn cần một máy luôn bật cho cổng phát luồng (thường là máy thu ngân, ít CPU), và quyền admin NVR để lấy luồng phụ (báo cáo nêu rủi ro mật khẩu NVR do thợ lắp giữ, và chưa rõ camera đám mây FPT/Viettel có mở RTSP không).
- Mất mạng thì cloud không nhận được video: không có cảnh báo trong lúc đó. Chế độ edge (ADR-0010) là phương án cho quán cần chạy khi mất mạng.
- Mỗi camera phải có luồng nhận riêng, đánh dấu theo mã camera (hiện đã có: `cam1`...).
- Số luồng giải mã đồng thời trên một GPU **chưa đo**.

## Phương án đã cân nhắc

- **Cloud kéo RTSP trực tiếp:** không xuyên được NAT.
- **JPEG từng khung cho mọi camera:** đơn giản, tái dùng code, nhưng tốn băng thông nhiều lần H.264 và cổng ở quán phải giải mã (CPU).
- **Cổng ở quán giải mã và làm mờ mặt trước khi gửi:** quyền riêng tư tốt hơn, nhưng cần GPU hoặc CPU mạnh ở quán, trái mục tiêu "không thiết bị". Là chế độ B/C.
- **Dịch vụ Live Stream API của Google:** hướng tới phát lại cho người xem, không hợp với suy luận theo khung. Chưa đánh giá chi tiết.
