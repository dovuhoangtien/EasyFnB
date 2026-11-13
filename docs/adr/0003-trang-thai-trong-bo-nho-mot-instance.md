# ADR-0003: Trạng thái ca trong RAM, một instance; cấu hình nằm ở bucket

- Trạng thái: Đề xuất. **Thay thế một phần bởi ADR-0013** cho kiến trúc đích (trạng thái ngoài RAM, nhiều instance). Vẫn đúng cho demo.
- Ngày: 2026-11-13

## Bối cảnh

`Hub` (`server/hub.py`) giữ việc, trạng thái bàn, nhật ký và danh sách người nghe SSE trong bộ nhớ tiến trình. Trên đĩa nó chỉ ghi `config.json` (vùng bàn, nhân viên, cài đặt), ảnh cắt `crops/` và bằng chứng `evidence/` dưới `DATA_DIR`. Phiên của trợ lý ADK dùng `InMemorySessionService`. Hai instance sẽ chia đôi dữ liệu. Báo cáo nghiên cứu đề xuất Firestore để đồng bộ nhiều instance, nhưng mã chưa dùng.

## Quyết định

1. **Một instance duy nhất:** `max_instance_count = 1`, và biến `min_instances` bị ràng buộc chỉ nhận 0 hoặc 1 (kiểm bằng `terraform test`).
2. **Việc và nhật ký ca giữ trong RAM**, chấp nhận mất khi khởi động lại.
3. **Cấu hình và ảnh** ghi vào bucket Cloud Storage gắn qua Cloud Run volume (gcsfuse) tại `/data`, với `DATA_DIR=/data`. Mặc định bật (`persist_data = true`), tắt được. Vòng đời bucket xoá sau 30 ngày.

## Hệ quả

- Không đổi dòng code nào trong server.
- Mỗi lần deploy là một lần khởi động lại: **việc đang mở và nhật ký ca mất**. Tránh deploy khi đang demo hoặc khi quán đang chạy ca.
- Vùng bàn, nhân viên và cài đặt sống qua deploy, nên không phải vẽ lại vùng bàn.
- Không scale ngang, không dự phòng. Chấp nhận cho demo; không dùng cho sản phẩm nhiều quán.
- gcsfuse không phải ổ đĩa cục bộ: ghi nhiều file nhỏ chậm hơn. Lượng ghi của app thấp (một file cấu hình, vài ảnh mỗi sự kiện) nhưng **chưa đo**. Nếu thấy chậm, đặt `persist_data = false` (DATA_DIR về `/tmp/easyfnb`, camera đẩy lại vùng bàn như `HUONG_DAN.md` mô tả).
- Cần Cloud Run gen2 (đã dùng).
- **Rủi ro bổ sung (phát hiện sau khi viết):** `hub.edge_event` và `_attach_evidence` ghi ảnh bằng `write_bytes` đồng bộ ngay trong handler `async`, chạy chung vòng lặp với SSE, MJPEG và WebSocket. Trên gcsfuse, mỗi lần ghi có thể chặn vòng lặp trong lúc chờ tải lên bucket (mỗi sự kiện 1 ảnh cắt cộng tối đa 3 ảnh bằng chứng). Mức chặn **chưa đo**. Nếu thấy hình trực tiếp hoặc thông báo đơ khi có sự kiện, đặt `persist_data = false` hoặc bọc các lần ghi bằng `asyncio.to_thread`.

## Phương án đã cân nhắc

- **Firestore làm nguồn sự thật:** đúng hướng khi nhiều quán/nhiều instance, nhưng phải viết lại `hub.py` và chuyển dashboard sang `onSnapshot`. Không kịp, và không cần cho một quán.
- **Cloud SQL / Memorystore:** thêm tiền cố định và quản trị cho một dịch vụ không cần.
- **Đĩa tạm `/tmp` (`DATA_DIR` mặc định trong Dockerfile):** đơn giản nhất nhưng mất cả cấu hình mỗi lần deploy.
