# ADR-0006: Terraform cho hạ tầng, Cloud Build cho image

- Trạng thái: Đề xuất
- Ngày: 2026-11-13

## Bối cảnh

Cách triển khai hiện tại là một lệnh `gcloud run deploy --source .` chạy tay (`HUONG_DAN.md`). Lệnh này tự tạo Artifact Registry `cloud-run-source-deploy` và gói build mặc định, nên hạ tầng không có chỗ nào ghi lại, không tái tạo được, và dễ lệch giữa máy này và máy khác. Nhóm muốn hạ tầng thành mã.

## Quyết định

- **Terraform** (≥ 1.6, provider `google ~> 7.0`) quản lý toàn bộ hạ tầng trong `infra/`: API, Cloud Run, service account, Secret Manager, bucket, Artifact Registry, giám sát, budget.
- **Cloud Build** (`infra/cloudbuild.yaml`) build image từ `easy-fnb/Dockerfile`, đẩy lên Artifact Registry, rồi chạy `gcloud run services update --image`. Chạy bằng tay qua `terraform output deploy_command`, dưới một service account riêng chỉ có quyền ghi log, đẩy image, cập nhật service này và đọc bucket mã nguồn.
- **Terraform không quản lý image sau lần đầu:** lần apply đầu dùng image mẫu `hello` của Google, `lifecycle.ignore_changes` bỏ qua trường `image`. Nhờ vậy `terraform apply` không đè image mà Cloud Build vừa đưa lên.
- Image gắn tag `BUILD_ID` và `latest`; revision luôn trỏ vào tag `BUILD_ID` để quay lui chính xác.
- **State:** mặc định cục bộ cho demo; khuyến nghị bucket GCS riêng (`backend.tf.example`) vì state chứa khoá (ADR-0005).

## Hệ quả

- Dựng lại từ đầu bằng `terraform apply` + một lệnh build. Dọn hết bằng `terraform destroy` (bucket `force_destroy = true`: **xoá luôn dữ liệu trong bucket**).
- Hai công cụ cùng chạm vào service: Terraform (cấu hình) và Cloud Build (image). Mọi thay đổi khác của revision qua `gcloud` bằng tay sẽ bị Terraform đè ở lần apply sau.
- Chưa có trigger tự động từ GitHub: kết nối kho mã cần một bước thủ công trong Console. Thêm sau khi cần.
- Lần apply đầu có thể lỗi vì API vừa bật chưa kịp lan truyền; chạy lại apply là qua.
- Bộ kiểm thử `infra/tests/offline.tftest.hcl` dùng provider giả, kiểm logic `count` và ràng buộc một instance. Nó **không** chứng minh apply thật thành công, vì chưa chạy trên project thật.

## Phương án đã cân nhắc

- **Giữ `gcloud run deploy --source .`:** ít việc nhất, không có IaC.
- **Terraform quản cả image (truyền `image` mỗi lần):** một công cụ duy nhất nhưng mọi deploy phải qua Terraform và cần build trước.
- **Pulumi / OpenTofu:** tương đương; chọn Terraform vì phổ biến và nhóm đã chọn.
- **Trigger GitHub ngay:** tốn thêm thao tác Console và quyền GitHub; không cần cho demo.
