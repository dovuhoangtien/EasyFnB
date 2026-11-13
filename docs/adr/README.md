# Architecture Decision Records

Mỗi file ghi một quyết định hạ tầng: bối cảnh, quyết định, hệ quả, phương án đã bỏ. Trạng thái **Đề xuất** nghĩa là nhóm chưa duyệt. Khi đổi quyết định, viết ADR mới và đánh dấu ADR cũ là *Thay thế bởi ADR-xxxx*, không sửa lịch sử.

| ADR | Quyết định | Trạng thái |
|---|---|---|
| [0001](0001-mot-service-cloud-run.md) | Một service Cloud Run chạy cả web và API | Đề xuất |
| [0002](0002-edge-tai-quan-cloud-nhan-su-kien.md) | AI nhìn chạy tại quán, cloud chỉ nhận sự kiện | Đề xuất |
| [0003](0003-trang-thai-trong-bo-nho-mot-instance.md) | Trạng thái ca trong RAM, một instance; cấu hình nằm ở bucket | Đề xuất |
| [0004](0004-gemini-api-key-va-lo-trinh-vertex.md) | Gemini bằng API key bây giờ, Vertex là bước sau | Đề xuất |
| [0005](0005-secret-manager-cho-khoa.md) | Khoá nằm trong Secret Manager | Đề xuất |
| [0006](0006-terraform-va-cloud-build.md) | Terraform cho hạ tầng, Cloud Build cho image | Đề xuất |
| [0007](0007-truy-cap-cong-khai-va-edge-key.md) | Mở công khai, chỉ camera có khoá; rủi ro được chấp nhận tạm | Đề xuất |
| [0008](0008-giong-doc-tren-dien-thoai.md) | Giọng đọc dùng của điện thoại, không đóng gói TTS vào container | Đề xuất |
| [0009](0009-chi-phi-va-giam-sat.md) | Cảnh báo ngân sách và uptime thay vì giới hạn cứng | Đề xuất |

Mẫu: [template.md](template.md).
