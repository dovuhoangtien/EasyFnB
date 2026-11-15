# ADR-0008: Giọng đọc dùng của điện thoại, không đóng gói TTS vào container

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Điện thoại nhân viên đọc việc mới qua tai nghe. `src/live/voice.ts` ưu tiên `GET /api/tts` (file wav từ máy chủ), và rơi về `speechSynthesis` với giọng `vi-VN` của máy khi máy chủ không có TTS. Ở máy chủ, `server/tts.py` chạy VieNeu hoặc Piper trong **một venv riêng ở đường dẫn Windows** (`C:\fnb-tts2`, `C:\fnb-tts`), tốn ~1,2 GB RAM, và model VieNeu tải ~580 MB từ Hugging Face khi chạy lần đầu. `Dockerfile` không cài các thứ này, nên trên Cloud Run `/api/tts/status` báo tắt. Báo cáo và đề tài đăng ký nêu Cloud TTS Chirp 3 HD, nhưng mã chưa gọi.

## Quyết định

Trên Cloud Run **không có TTS phía máy chủ**. Điện thoại đọc bằng giọng tiếng Việt của máy. Không đóng gói VieNeu/Piper vào image và không thêm Cloud TTS trong đợt này.

## Hệ quả

- Image nhỏ, khởi động nhanh, RAM 1 GiB đủ.
- **Chất lượng giọng phụ thuộc điện thoại:** máy không có giọng tiếng Việt thì không đọc được. Phải thử từng máy dùng khi demo (iPhone và Android khác nhau). Chưa kiểm tra.
- Demo cục bộ trên laptop (`chay_may_chu.bat`) vẫn có giọng VieNeu như trước.
- Giọng mất khi chuyển từ laptop sang Cloud Run; cần nói rõ khi trình bày.

## Phương án đã cân nhắc

- **Đóng gói VieNeu vào container (CPU):** 1,2 GB RAM + 580 MB tải model, khởi động 7–12 giây, tăng chi phí instance và cần viết lại đường dẫn Windows. Không kịp.
- **Cloud Text-to-Speech (Chirp 3 HD):** đúng với đề xuất ban đầu; cần thêm API, quyền, code gọi và cache wav. Là bước kế tiếp hợp lý, nên làm cùng lúc với chuyển Vertex (ADR-0004).
- **Giữ giọng ở laptop, Cloud Run chỉ làm dashboard:** làm mất lý do dùng Cloud Run cho nhân viên.
