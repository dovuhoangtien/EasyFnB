output "service_url" {
  description = "Địa chỉ của app (trang quản lý, điện thoại nhân viên, API cho camera)."
  value       = google_cloud_run_v2_service.app.uri
}

output "edge_key" {
  description = "Khoá chung cho camera: đặt vào biến môi trường EDGE_KEY trên máy chạy camera. Lấy bằng: terraform output -raw edge_key"
  value       = random_password.edge_key.result
  sensitive   = true
}

output "image_repo" {
  description = "Đường dẫn image (không có tag) mà cloudbuild.yaml đẩy lên."
  value       = local.image_repo
}

output "build_service_account" {
  description = "Tài khoản dịch vụ chạy Cloud Build."
  value       = google_service_account.build.email
}

output "build_source_bucket" {
  description = "Bucket tạm chứa mã nguồn khi chạy gcloud builds submit."
  value       = google_storage_bucket.build_src.name
}

output "data_bucket" {
  description = "Bucket gắn làm DATA_DIR (null nếu persist_data = false)."
  value       = var.persist_data ? google_storage_bucket.data[0].name : null
}

output "deploy_command" {
  description = "Lệnh build và deploy bản mới (chạy từ thư mục gốc của repo)."
  value       = <<-EOT
    gcloud builds submit easy-fnb --project ${var.project_id} --config infra/cloudbuild.yaml `
      --service-account projects/${var.project_id}/serviceAccounts/${google_service_account.build.email} `
      --gcs-source-staging-dir gs://${google_storage_bucket.build_src.name}/src `
      --substitutions _IMAGE=${local.image_repo},_SERVICE=${var.service_name},_REGION=${var.region}
  EOT
}

output "camera_command" {
  description = "Lệnh chạy camera đẩy lên Cloud Run (PowerShell, từ thư mục gốc của repo)."
  value       = <<-EOT
    $env:EDGE_KEY = (terraform -chdir=infra output -raw edge_key)
    vision-test\chay_camera.bat <nguồn> ${google_cloud_run_v2_service.app.uri} cam1
  EOT
}
