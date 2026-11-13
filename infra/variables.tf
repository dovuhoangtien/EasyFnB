variable "project_id" {
  description = "ID của project Google Cloud (đã gắn billing)."
  type        = string
}

variable "region" {
  description = "Vùng đặt Cloud Run, Artifact Registry, bucket. Singapore gần Việt Nam nhất."
  type        = string
  default     = "asia-southeast1"
}

variable "service_name" {
  description = "Tên service Cloud Run."
  type        = string
  default     = "easy-fnb"
}

variable "image" {
  description = "Image khởi tạo cho lần apply đầu. Sau đó Cloud Build đổi image (Terraform bỏ qua trường này, xem ADR-0006)."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "min_instances" {
  description = "1 = luôn bật (bộ đếm chuyển việc vẫn chạy khi không ai mở trang), tốn tiền cả ngày. 0 = ngủ khi rảnh, chỉ dùng khi không demo."
  type        = number
  default     = 1

  validation {
    condition     = var.min_instances == 0 || var.min_instances == 1
    error_message = "Chỉ 0 hoặc 1: trạng thái nằm trong bộ nhớ, không chạy được nhiều hơn một instance (ADR-0003)."
  }
}

variable "cpu" {
  description = "Số vCPU của instance."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "RAM của instance. 1Gi vì google-adk (trợ lý) nạp thêm khá nhiều thư viện; HUONG_DAN.md dùng 512Mi khi chưa có trợ lý."
  type        = string
  default     = "1Gi"
}

variable "allow_unauthenticated" {
  description = "Cho mọi người gọi service (cần vì điện thoại nhân viên và camera không có tài khoản Google). Tổ chức chặn allUsers thì đặt false và dùng proxy/IAP."
  type        = bool
  default     = true
}

variable "persist_data" {
  description = "Gắn bucket Cloud Storage làm DATA_DIR để vùng bàn, nhân viên, cài đặt, ảnh cắt sống qua lần khởi động lại (mỗi lần deploy là một lần khởi động lại). ADR-0003."
  type        = bool
  default     = true
}

variable "data_retention_days" {
  description = "Số ngày giữ ảnh cắt và bằng chứng trong bucket dữ liệu (ảnh đã làm mờ mặt ở camera, nhưng vẫn là dữ liệu của quán)."
  type        = number
  default     = 30
}

variable "gemini_api_key" {
  description = "Khoá Gemini (AI Studio). Để trống thì app vẫn chạy, chỉ không có kiểm tra ảnh và trợ lý ADK. Truyền bằng TF_VAR_gemini_api_key, đừng ghi vào file."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kie_api_key" {
  description = "Khoá kie.ai (đường dự phòng khi chưa có khoá Gemini). Có khoá này thì kiểm tra ảnh và tóm tắt đi qua kie.ai; trợ lý vẫn cần khoá Gemini."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_vertex_ai" {
  description = "Bật API Vertex AI và cấp roles/aiplatform.user cho service account của app. Code hiện chưa gọi Vertex (ADR-0004); đây là chuẩn bị cho lộ trình dùng credit Cloud."
  type        = bool
  default     = false
}

variable "billing_account" {
  description = "ID billing account (dạng 012345-6789AB-CDEF01) để tạo budget. Để trống thì bỏ qua budget."
  type        = string
  default     = ""
}

variable "budget_usd" {
  description = "Ngưỡng ngân sách tháng, USD. Cảnh báo ở 50%, 90%, 100%."
  type        = number
  default     = 100
}

variable "alert_email" {
  description = "Email nhận cảnh báo ngân sách và cảnh báo máy chủ không phản hồi. Để trống thì bỏ qua cảnh báo máy chủ."
  type        = string
  default     = ""
}
