# ADR-0010: Suy luận chạy trên cloud, edge là một lựa chọn

- Trạng thái: Đề xuất (kiến trúc đích; **ngoài phạm vi IaC demo**)
- Ngày: 2026-11-13
- Thay thế một phần: ADR-0002 (ADR-0002 vẫn đúng cho chế độ edge và cho demo)

## Bối cảnh

ADR-0002 đặt suy luận ở laptop GPU tại quán. Với một quán và một demo, nó chạy được. Với sản phẩm:

- Pipeline demo chạy khoảng 6 model nặng (YOLO26n-pose, YOLO26s, YOLOE-26s-seg, RTMPose-m, PE-Core S/16, PE-Core B/16) cộng 3 đầu phân loại nhỏ và ByteTrack. Chi phí mỗi khung nhân theo số người trong cảnh.
- Số đo trên RTX 3050 4 GB (`vision-test/KET_QUA.md`): ~57 khung/giây bản nhanh, ~24 bản nhạy; ~11 camera ở bản nhanh, ~5 ở bản nhạy, chỉ 2 khi quán rất đông (5 khung/giây mỗi camera).
- Mỗi quán một máy GPU: engine TensorRT gắn với GPU đã build ra nó, cập nhật model phải đến từng quán, máy hỏng là mất dịch vụ.
- Quán thường không có máy GPU và báo cáo đặt điều kiện "không mua phần cứng".

## Quyết định

Kiến trúc đích đưa **suy luận, điều phối và AI lên Google Cloud**. Quán chỉ có cổng phát luồng (không giải mã, không GPU) và nhận kết quả qua điện thoại và trình duyệt.

**Edge giữ lại như một lựa chọn** trong ba chế độ dùng chung hợp đồng `/api/edge/*`: A chỉ cloud (mặc định đích), B lai (edge lọc trước), C edge đầy đủ (như demo). Hub không phân biệt sự kiện đến từ chế độ nào.

Demo hiện tại và IaC trong `infra/` **không đổi**: demo chạy chế độ C.

## Hệ quả

- Chi phí GPU cloud trở thành khoản lớn nhất và chưa biết: phụ thuộc k (GPU cloud nhanh hơn 3050 bao nhiêu lần) và g (tỉ lệ khung còn lại sau lọc). Ước tính trong `docs/architecture.md` mục 3.1 cho thấy chi phí báo cáo (~$3/quán/tháng) thấp hơn thực tế khoảng một bậc độ lớn, vì báo cáo giả định một detector nano.
- Video thô có mặt người rời quán (ADR-0014).
- Cần băng thông lên ở quán (ADR-0011).
- Phải refactor pipeline: hiện là một tiến trình làm tất cả; tách tầng ở ADR-0012. Pha P1 chỉ lift-and-shift để đo trước.
- Chế độ C vẫn cần cho quán không đồng ý đưa video ra ngoài hoặc cần chạy khi mất mạng.

## Phương án đã cân nhắc

- **Giữ edge là mặc định:** không scale, vận hành từng quán, nhưng không phụ thuộc đường truyền và quyền riêng tư tốt nhất. Giữ lại thành chế độ C.
- **Chỉ edge, bỏ cloud GPU:** đơn giản nhất cho một quán, không giải quyết nhiều quán.
- **Cho Gemini nhìn trực tiếp mọi camera:** báo cáo ước tính ~$435/tháng cho 8 camera (mỗi 5 giây một lần); chỉ dùng để xác minh.
- **Dùng dịch vụ có sẵn (Video Intelligence API):** không hợp với bộ nhận diện riêng (giơ tay, nhân viên/khách, bàn). Chưa đánh giá chi tiết.
