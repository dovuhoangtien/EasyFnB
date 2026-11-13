# ADR-0004: Gemini bằng API key bây giờ, Vertex là bước sau

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Mã gọi Gemini ở hai chỗ:

- `server/gemini.py`: gọi REST `generativelanguage.googleapis.com` bằng `httpx`, header `x-goog-api-key`. Không đọc Application Default Credentials.
- `server/tro_ly.py`: trợ lý dùng Google ADK, chỉ bật khi `GEMINI_API_KEY` không rỗng (`adk_wanted`).

Báo cáo (`Easy FnB không mua phần cứng.md`) cảnh báo: khoản credit $300 dùng thử và credit sự kiện **có thể không trả được cho API key AI Studio** nếu billing account mở sau 2/3/2026, và nên gọi qua Vertex / Gemini Enterprise Agent Platform bằng service account. Mình **chưa kiểm chứng** điều này; cần xác nhận với ban tổ chức hoặc bằng cách thử. Hiện nhóm chưa có khoá Gemini và đang dùng kie.ai làm đường tạm (`HUONG_DAN.md`).

## Quyết định

- **Hạ tầng demo dùng khoá API:** `GEMINI_API_KEY` (và tùy chọn `KIE_API_KEY`) nằm trong Secret Manager (ADR-0005). Không sửa code.
- **Chuẩn bị sẵn đường Vertex:** biến `enable_vertex_ai` (mặc định `false`) bật API `aiplatform.googleapis.com` và cấp `roles/aiplatform.user` cho service account của app.
- **Chuyển sang Vertex là việc code riêng,** chưa làm: đổi `gemini.py` sang SDK `google-genai` với `vertexai=True`, và bỏ điều kiện `GEMINI_API_KEY` trong `adk_wanted`. ADK có thể dùng Vertex qua `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, nhưng cổng `adk_wanted` hiện chặn trước.

## Hệ quả

- Nếu credit không trả được cho khoá AI Studio, khoản Gemini sẽ tính vào thẻ cá nhân; lượng nhỏ nhưng khác với kỳ vọng "0 đồng tiền túi" của báo cáo. **Nên hỏi ban tổ chức trước ngày demo.**
- Khoá API nằm trong env của Cloud Run (qua secret) và trong state Terraform nếu truyền qua `TF_VAR_gemini_api_key` (ADR-0005).
- Endpoint Vertex `global` không đảm bảo nơi xử lý dữ liệu; endpoint theo vùng đắt hơn ~10% (báo cáo). Cần quyết khi chuyển.
- Khi chuyển Vertex xong, bỏ biến khoá khỏi Terraform, giảm bề mặt bí mật.

## Phương án đã cân nhắc

- **Chuyển Vertex ngay:** an toàn hơn về khoá và credit, nhưng phải sửa và kiểm thử hai module ngay trước demo.
- **Chỉ dùng kie.ai:** chậm 20–80 giây mỗi lượt, không có trợ lý ADK; chỉ là đường dự phòng.
- **Gemma tại chỗ:** báo cáo nêu như dự phòng offline, chưa thử.
