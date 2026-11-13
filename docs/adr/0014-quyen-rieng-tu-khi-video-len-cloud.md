# ADR-0014: Quyền riêng tư khi video lên cloud

- Trạng thái: Đề xuất (kiến trúc đích; **cần đánh giá pháp lý**; ngoài phạm vi IaC demo)
- Ngày: 2026-11-13

## Bối cảnh

Ở demo, pipeline làm mờ mặt khách (`blur_faces` trong `fnb_common.py`, dựa trên khung xương: mũi, mắt, tai) **trước khi** bất kỳ ảnh nào rời máy (`easyfnb_test.py` ghi: "làm mờ mặt trên mọi ảnh rời máy"). Khi suy luận lên cloud (ADR-0010), video thô có mặt người **rời quán** vì chính cloud mới có khung xương để làm mờ.

Báo cáo (`Công nghệ AI cho Easy FnB`, `Bài toán tương tự ngành khác`) nhắc Luật 91/2025 xếp khuôn mặt vào dữ liệu nhạy cảm và đề xuất làm mờ mặt trước khi gửi lên cloud và Gemini. Nhóm **chưa có đánh giá pháp lý**.

## Quyết định

1. **Khung thô chỉ tồn tại trong RAM** của tiền xử lý, hàng khung (TTL vài giây) và worker. Không ghi đĩa, Cloud Storage, nhật ký hay metric.
2. **Làm mờ mặt ở worker, ngay khi có khung xương, trước khi** lưu hoặc gửi bất kỳ ảnh nào: ảnh bằng chứng, khung xem trực tiếp, ảnh gửi Gemini. Không làm được ở tiền xử lý vì chưa có khung xương.
3. **Mạng riêng cho các tầng giữ khung thô** (hàng khung, suy luận); chỉ cổng nhận video và hub ra Internet; TLS mọi chặng.
4. **Vùng dữ liệu** cố định (`asia-southeast1` cho cả suy luận và lưu trữ); Gemini qua endpoint theo vùng khi cần kiểm soát nơi xử lý (đắt hơn ~10% theo báo cáo; endpoint `global` không đảm bảo nơi xử lý).
5. **Chế độ C (edge đầy đủ)** vẫn là lựa chọn cho quán không đồng ý đưa video ra ngoài.
6. **Chủ quán đồng ý bằng văn bản** và có biển báo tại quán trước khi bật chế độ A/B.

## Hệ quả

- Mặt không bao giờ được lưu, nhưng **có xuất hiện trong RAM trên cloud** vài giây. Mức đó có chấp nhận được hay không là quyết định pháp lý, không phải kỹ thuật.
- Lỗi phần mềm có thể làm lộ khung thô (nhật ký debug, dump khi lỗi). Cần quy tắc: không log ảnh, tắt core dump, kiểm thử tự động rằng ảnh rời worker đều đã qua làm mờ.
- Làm mờ chỉ tốt bằng khung xương: người quay lưng hoặc bị che có thể sót (báo cáo đề xuất YuNet làm lưới dự phòng).
- Chi phí: chạy thêm mô hình phát hiện mặt (nhỏ) ở worker nếu cần lưới dự phòng.
- Yêu cầu của quán có thể đổi chế độ triển khai theo từng quán.

## Phương án đã cân nhắc

- **Làm mờ ở cổng phát luồng trong quán:** mặt không rời quán, nhưng cần CPU/GPU ở quán và model phát hiện mặt, trái mục tiêu "không thiết bị". Là chế độ B.
- **Lưu video thô để huấn luyện:** hữu ích cho cải tiến model, nhưng nâng rủi ro rất nhiều; bị loại, thu thập dữ liệu huấn luyện đi đường riêng có đồng ý.
- **Không làm gì thêm so với demo:** không phù hợp vì cơ sở của demo (mặt không rời quán) không còn đúng.
