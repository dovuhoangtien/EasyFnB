# ADR-0012: Tách suy luận GPU không trạng thái khỏi worker camera có trạng thái

- Trạng thái: Đề xuất (kiến trúc đích; **ngoài phạm vi IaC demo**)
- Ngày: 2026-11-13

## Bối cảnh

`vision-test/easyfnb_test.py` là một tiến trình làm tất cả: đọc video, giải mã, chạy các model, bộ bám ByteTrack, vùng bàn, máy trạng thái, làm mờ mặt, tạo sự kiện, gửi lên server. Nó có **trạng thái theo camera**: track id, `rtm_cache` (khung xương RTMPose lần trước theo track), cửa sổ nhân viên/khách 10 giây, trạng thái và ảnh sạch của từng bàn. Còn các model thì **không có trạng thái**: nhận ảnh, trả khung xương, hộp hoặc xác suất.

Chạy mỗi camera một tiến trình riêng (cách hiện tại) không gộp lô được giữa các camera và nạp lại model ở từng tiến trình. GPU chỉ có 4 GB ở máy demo và PE-Core L/14 đã tràn bộ nhớ khi thử, nên bộ nhớ GPU cũng là ràng buộc.

## Quyết định

Tách hai loại:

1. **Dịch vụ suy luận GPU không trạng thái** (Triton Inference Server, engine TensorRT): YOLO pose, YOLO đồ vật, YOLOE, RTMPose, bộ mã hoá ảnh PE-Core S/B cùng các đầu phân loại. Nhận ảnh từ nhiều camera, **gộp lô động**, nhân bản được, thay thế được.
2. **Worker camera chạy CPU, có trạng thái**: tracker, vùng bàn, máy trạng thái, làm mờ mặt, tạo sự kiện. **Chia theo camera** (băm nhất quán). Mỗi camera có đúng một worker đang giữ.

Worker gọi suy luận qua gRPC. Pha P1 (lift and shift, một VM GPU chạy nhiều tiến trình hiện có) có trước để đo; tách tầng là P2.

## Hệ quả

- Có thể nhân bản GPU theo tải độc lập với số camera, và đổi loại GPU mà chỉ phải build lại engine (kho model, CI).
- Worker chết: camera chuyển sang worker khác, dựng lại trạng thái trong im lặng vài giây (demo hiện cần ~4 giây khi vòng video lặp lại, `HUONG_DAN.md`). Việc đang chờ trên bàn có thể bị trễ hoặc phát lại; cần chốt hành vi khử trùng sự kiện (`eid` đã có).
- Thêm một bước mạng giữa worker và suy luận, nằm trong ngân sách độ trễ (~150 ms, chưa đo).
- Làm mờ mặt cần khung xương nên nằm ở worker (ADR-0014).
- Đây là refactor thật: chia `easyfnb_test.py` thành client suy luận và logic camera. Không đổi được bằng cấu hình.
- Lợi ích gộp lô thực tế **chưa đo**.

## Phương án đã cân nhắc

- **Mỗi camera một tiến trình có model riêng (hiện tại):** đơn giản; tốn bộ nhớ GPU theo số camera, không gộp lô.
- **Một dịch vụ khối chứa cả suy luận và trạng thái:** ít thành phần; không scale độc lập, failover mất cả hai.
- **Đưa trạng thái ra Redis để worker không trạng thái:** tracker cập nhật mỗi khung, độ trễ và chi phí ghi đọc cao; chia theo camera rẻ hơn.
- **Cloud Run GPU hay GKE:** cả hai chạy được Triton. Cloud Run GPU ít vận hành hơn nhưng giá và quota ở `asia-southeast1` chưa xác nhận (báo cáo ghi chưa rõ). Quyết khi đo ở P1.
