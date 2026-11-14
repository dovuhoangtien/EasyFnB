# ADR-0015: Co giãn, backpressure, suy giảm có kiểm soát và SLO

- Trạng thái: Đề xuất (kiến trúc đích; **ngoài phạm vi IaC demo**)
- Ngày: 2026-11-13

## Bối cảnh

Tải suy luận thay đổi theo số camera, số người trong cảnh (RTMPose và PE-Core chạy trên từng người) và giờ trong ngày. Mọi quán ở Việt Nam đông cùng bữa trưa và bữa tối, nên tải đỉnh chồng lên nhau (suy luận, chưa đo). `KET_QUA.md` cho thấy clip đông nhất làm tốc độ rơi từ 57 xuống 35 khung/giây (bản nhanh) và từ 24 xuống 11 (bản nhạy). Gemini có quota theo project và độ trễ giây. Hub phục vụ kết nối giữ lâu.

Mất khung chịu được; mất sự kiện thì không (ADR-0013).

## Quyết định

1. **Co giãn GPU** theo độ sâu hàng khung và mức dùng GPU (mục tiêu ~0,6 đỉnh), không theo số quán. Tắt ngoài giờ mở cửa. Worker camera co giãn theo số camera.
2. **Backpressure bằng cách bỏ khung**, không bằng cách xếp hàng: hàng khung chỉ giữ khung mới nhất mỗi camera.
3. **Suy giảm theo bậc khi quá tải**, theo thứ tự: (a) bỏ khung cũ; (b) hạ khung/giây camera vắng; (c) bỏ RTMPose, dùng khung xương YOLO (bản "nhanh" thay "nhạy"); (d) chỉ giữ "gọi phục vụ" và "bàn cần dọn", ngừng xét hành động chi tiết; (e) từ chối camera mới và báo vận hành. Mỗi bậc ghi vào nhật ký để quán biết.
4. **Công bằng giữa các quán:** hạn mức khung/giây theo quán, để một quán đông không làm quán khác chậm.
5. **Gemini:** hàng đợi, giới hạn tốc độ theo quota, hạn chót vài giây; quá hạn thì báo "chưa xác minh" (demo đã có), không chặn đường báo việc.
6. **SLO đề xuất:** từ lúc điều kiện báo đã đủ đến lúc điện thoại nhận, **p95 ≤ 1,5 giây**; sự kiện không mất (khử trùng bằng `eid`); độ sẵn sàng theo giờ mở cửa. Đo từng chặng theo ngân sách ở `docs/architecture.md` mục 4.
7. **Đo trước khi tin:** các con số k (tốc độ L4 so với 3050), g (tỉ lệ khung sau lọc), băng thông, độ trễ mạng, số luồng giải mã đều **chưa đo** và là việc đầu tiên của pha P1.

## Hệ quả

- Hệ thống hạ chất lượng có kiểm soát thay vì chậm dần hoặc sập; bù lại độ chính xác giảm khi tải cao. Bản "nhanh" đã đo gần ngang bản "nhạy" ở trạng thái bàn (130/137 so với 130/137) nhưng giơ tay chậm hơn (1,37 giây so với 0,40 giây).
- Cần giám sát theo từng chặng (Cloud Monitoring): độ sâu hàng, mức dùng GPU, độ trễ từng chặng, tỉ lệ bỏ khung, bậc suy giảm hiện tại.
- Chia công bằng giữa các quán thêm logic điều phối ở đầu vào.
- Chi phí cố định cao hơn khi giữ GPU tối thiểu để tránh khởi động lạnh (báo cáo ghi ~5 giây cho Cloud Run GPU; chưa kiểm).

## Phương án đã cân nhắc

- **Xếp hàng không giới hạn:** không mất khung nhưng độ trễ tăng không giới hạn, báo việc đến muộn là vô nghĩa.
- **Cấp GPU theo đỉnh:** an toàn, tốn tiền gấp nhiều lần vì tải đỉnh chỉ vài giờ mỗi ngày.
- **Từ chối khi quá tải ngay:** đơn giản, nhưng bỏ quán trong lúc họ cần nhất.
