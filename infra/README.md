# Hạ tầng Google Cloud (Terraform)

Thiết kế: [`../docs/infra-design.md`](../docs/infra-design.md). Lý do từng quyết định: [`../docs/adr/`](../docs/adr/README.md).

Tạo: Cloud Run `easy-fnb`, hai service account, Secret Manager, Artifact Registry, hai bucket (sao lưu hoặc dữ liệu, mã nguồn build), và tùy chọn: uptime check, cảnh báo email, budget.

> **Trạng thái:** đã qua `terraform validate` và `terraform test` (provider giả). **Chưa apply lên project thật.** Lần apply đầu có thể lộ lỗi quyền hoặc quota; xem mục "Sự cố thường gặp".

## Cần có

- Terraform ≥ 1.6, Google Cloud CLI.
- Một project đã gắn billing; người chạy có quyền Owner (hoặc Editor + Security Admin + Service Account Admin).
- Đăng nhập hai lần: `gcloud auth login` và `gcloud auth application-default login`.

## State (khuyến nghị, một lần)

State chứa `EDGE_KEY` và khoá LLM (ADR-0005). Tạo bucket riêng rồi bật backend:

```powershell
gcloud storage buckets create gs://<PROJECT_ID>-easy-fnb-tfstate --project <PROJECT_ID> --location asia-southeast1 --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://<PROJECT_ID>-easy-fnb-tfstate --versioning
Copy-Item infra\backend.tf.example infra\backend.tf   # sửa <PROJECT_ID>
```

Bỏ qua bước này thì state nằm ở `infra\terraform.tfstate` trên máy bạn (đã được `.gitignore`).

## Dựng hạ tầng

```powershell
cd infra
Copy-Item terraform.tfvars.example terraform.tfvars    # điền project_id
$env:TF_VAR_gemini_api_key = '<khoá>'                  # tùy chọn; kie.ai: TF_VAR_kie_api_key
terraform init
terraform plan
terraform apply
```

Lần apply đầu chạy một service **image mẫu** (`hello`) để hạ tầng đứng lên trước khi có image thật.

## Build và deploy app

Từ thư mục gốc của repo:

```powershell
terraform -chdir=infra output -raw deploy_command    # in ra lệnh, copy rồi chạy
```

Lệnh `gcloud builds submit` build `easy-fnb/Dockerfile`, đẩy lên Artifact Registry và cập nhật Cloud Run. Lệnh này đã bọc sẵn `--substitutions` trong nháy kép nên chạy được ngay trên PowerShell (không bị lỗi tách tham số ở dấu phẩy). Deploy là một lần khởi động lại: việc đang mở và cảnh báo trong RAM mất, nhưng lịch sử và cấu hình được khôi phục từ bucket sao lưu (ADR-0003).

## Kiểm tra

1. `terraform -chdir=infra output -raw service_url` rồi mở `<url>/api/health`, phải thấy `"ok": true`.
2. Mở `<url>/` → Cài đặt → Kết nối → **Thử kết nối** (có khoá Gemini thì thấy tên model).
3. Chạy camera đẩy lên Cloud Run:

```powershell
$env:EDGE_KEY = (terraform -chdir=infra output -raw edge_key)
vision-test\chay_camera.bat clips\01_phong_an_goc_cao.mp4 <url> cam1
```

## Sau demo

```powershell
terraform apply -var min_instances=0     # ngủ khi rảnh, hết tốn tiền instance
terraform destroy                        # xoá tất cả, kể cả dữ liệu trong bucket (force_destroy)
```

## Biến chính

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `project_id` | bắt buộc | |
| `region` | `asia-southeast1` | |
| `min_instances` | `1` | Chỉ nhận 0 hoặc 1; luôn `max = 1` |
| `memory` / `cpu` | `2Gi` / `1` | `DATA_DIR` là `/tmp` (RAM) khi không `persist_data`; chưa đo với code mới |
| `persist_data` | `false` | Gắn bucket (gcsfuse) làm `DATA_DIR`. Mặc định tắt (dùng sao lưu Litestream thay thế). Bật lên thì bỏ qua `backup_data` |
| `backup_data` | `true` | Sao lưu `DATA_DIR` lên bucket Cloud Storage: Litestream cho `timeline.db` và `quan.db` (5s), script đồng bộ cho `config.json`, `staff/`, `chat/` (10s). Khôi phục khi khởi động. Bỏ qua khi `persist_data = true` (ADR-0003) |
| `clips_max_mb` | `200` | Trần thư mục clip (`CLIPS_MAX_MB`); mặc định của máy chủ là 2000, quá lớn khi `DATA_DIR` là RAM |
| `tts_voice` | `vi-VN-Chirp3-HD-Aoede` | Giọng Google Cloud Text-to-Speech cho điện thoại nhân viên (`TTS_ENGINE=google`) |
| `gemini_model`, `gemini_verify_model` | rỗng | `gemini_verify_model = "gemini-decision-1"` bật Gemini Decision để kiểm tra ảnh |
| `gemini_api_key`, `kie_api_key` | rỗng | Truyền bằng `TF_VAR_*`, không ghi vào file |
| `allow_unauthenticated` | `true` | Xem ADR-0007 |
| `enable_vertex_ai` | `false` | Chuẩn bị Vertex, mã chưa dùng (ADR-0004) |
| `billing_account`, `budget_usd`, `alert_email` | rỗng / `100` / rỗng | Budget và cảnh báo |

Danh sách đầy đủ: `variables.tf`. Kiểm tra logic không cần tài khoản Google: `terraform test`.

## Sự cố thường gặp

- **`API has not been used ... or it is disabled`** ngay lần apply đầu: API vừa bật chưa lan truyền. Chờ một phút, chạy lại `terraform apply`.
- **`One or more users named in the policy do not belong to a permitted customer`** khi cấp `allUsers`: tổ chức chặn truy cập công khai. Đặt `allow_unauthenticated = false` (rồi điện thoại và camera cần một lớp xác thực khác, ADR-0007).
- **Tạo budget bị từ chối quyền:** cần `billing.budgets.create` trên billing account. Để `billing_account` trống và tạo budget trong Console.
- **Build thất bại ở bước đẩy image:** service account build cần chút thời gian để quyền có hiệu lực sau lần apply đầu; chạy lại lệnh build.
- **Cloud Run không đọc được secret:** secret chưa có version. Chỉ xảy ra nếu bạn tự xoá version; chạy lại `terraform apply`.
