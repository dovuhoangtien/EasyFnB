# ADR-0005: Khoá nằm trong Secret Manager

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Server đọc ba khoá từ biến môi trường: `EDGE_KEY`, `GEMINI_API_KEY`, `KIE_API_KEY`. `HUONG_DAN.md` hiện truyền chúng bằng `--set-env-vars`, nghĩa là khoá hiện rõ trong cấu hình service và trong lịch sử lệnh của máy. Tệp `.env` không được đưa vào image (`.dockerignore`).

## Quyết định

Mỗi khoá là một secret trong Secret Manager, gắn vào Cloud Run bằng `value_source.secret_key_ref` với `version = "latest"`. Service account của app có `secretAccessor` **trên từng secret**, không phải cả project.

- `EDGE_KEY`: Terraform sinh bằng `random_password` (40 ký tự) và lưu thành version. Lấy ra cho máy camera bằng `terraform output -raw edge_key`.
- `GEMINI_API_KEY`, `KIE_API_KEY`: chỉ tạo khi truyền biến `TF_VAR_gemini_api_key` / `TF_VAR_kie_api_key`. Không truyền thì không có secret và app chạy không AI.

## Hệ quả

- Khoá không hiện trong cấu hình Cloud Run hay log deploy; có thể xoay khoá bằng cách thêm version mới (cần revision mới để instance đọc lại `latest`).
- **Giá trị khoá nằm trong state Terraform** (`random_password`, `secret_data`). State phải ở bucket riêng, không công khai, có versioning (`infra/README.md`, mục State), và không được commit. `infra/.gitignore` đã chặn `*.tfstate` và `terraform.tfvars`.
- Ba khoá tùy chọn bằng `count` làm cấu hình dài hơn, bù lại không bao giờ có secret rỗng (secret không có version làm deploy Cloud Run thất bại).
- Khoá trên máy camera (`EDGE_KEY`) vẫn là biến môi trường của người dùng Windows; Secret Manager không che được phần đó.

## Phương án đã cân nhắc

- **`--set-env-vars` như `HUONG_DAN.md`:** nhanh nhất, nhưng khoá rõ trong cấu hình.
- **Write-only attribute (`secret_data_wo`) để khoá không vào state:** tốt hơn, cần Terraform ≥ 1.11 và provider mới; chưa dùng để tránh rủi ro tương thích lúc sát demo. Nên làm khi ổn định.
- **Tạo secret rỗng, nạp khoá bằng `gcloud secrets versions add`:** khoá không vào state, nhưng phải nạp tay trước khi deploy và dễ quên.
