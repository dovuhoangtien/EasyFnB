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
  description = "RAM của instance. Khi persist_data = false, DATA_DIR nằm trong /tmp = RAM nên clip, ảnh cắt và hai file SQLite cũng tính vào đây: chừa chỗ cho clips_max_mb. Chưa đo với code mới; google-adk (trợ lý) cũng nạp khá nhiều thư viện."
  type        = string
  default     = "2Gi"
}

variable "clips_max_mb" {
  description = "Trần dung lượng thư mục clip xem lại (CLIPS_MAX_MB). Máy chủ nhận clip tối đa 40 MB mỗi cái và mặc định cho phép 2000 MB, quá lớn khi DATA_DIR là RAM. Phải nhỏ hơn nhiều so với memory."
  type        = number
  default     = 200

  validation {
    condition     = var.clips_max_mb >= 0
    error_message = "clips_max_mb không được âm."
  }
}

variable "backup_data" {
  description = "Sao lưu DATA_DIR lên bucket Cloud Storage: Litestream cho timeline.db và quan.db, script đồng bộ cho config.json và ảnh nhân viên, ảnh chat. Khởi động lại thì khôi phục. Bỏ qua khi persist_data = true. ADR-0003."
  type        = bool
  default     = true
}

variable "demo_feed" {
  description = "Bản demo tự chạy: phát clip đã che mặt làm hình camera, tự tạo việc và cho nhân viên ảo nhận việc. Tắt khi nối camera thật (có camera thật gửi hình thì máy chủ cũng tự dừng)."
  type        = bool
  default     = true
}

variable "backup_prefix" {
  description = "Thư mục trong bucket sao lưu. Đổi sang tên mới (ví dụ data2) rồi apply thì instance khởi động với thư mục dữ liệu trống và máy chủ nạp lại dữ liệu demo (server/du_lieu_demo)."
  type        = string
  default     = "data"
}

variable "tts_voice" {
  description = "Giọng Google Cloud Text-to-Speech cho điện thoại nhân viên (GOOGLE_TTS_VOICE). Ví dụ vi-VN-Chirp3-HD-Aoede (nữ), vi-VN-Chirp3-HD-Charon (nam), vi-VN-Neural2-A (rẻ hơn)."
  type        = string
  default     = "vi-VN-Chirp3-HD-Aoede"
}

variable "gemini_model" {
  description = "Model Gemini cho trợ lý và tóm tắt ca (GEMINI_MODEL). Để trống thì dùng mặc định của máy chủ (gemini-3.5-flash-lite)."
  type        = string
  default     = ""
}

variable "gemini_verify_model" {
  description = "Model kiểm tra ảnh báo động (GEMINI_VERIFY_MODEL). Đặt gemini-decision-1 để dùng Gemini Decision (Decisions API, trả xác suất có/không). Để trống thì kiểm tra ảnh bằng generateContent như cũ."
  type        = string
  default     = ""
}

variable "allow_unauthenticated" {
  description = "Cho mọi người gọi service (cần vì điện thoại nhân viên và camera không có tài khoản Google). Tổ chức chặn allUsers thì đặt false và dùng proxy/IAP."
  type        = bool
  default     = true
}

variable "persist_data" {
  description = "Gắn bucket Cloud Storage (gcsfuse) làm DATA_DIR để vùng bàn, nhân viên, cài đặt, ảnh cắt sống qua lần khởi động lại. Mặc định TẮT vì server ghi hai file SQLite (timeline.db, quan.db) ở chế độ WAL, mà WAL cần bộ nhớ chia sẻ gcsfuse không hỗ trợ tốt (chưa kiểm). Tắt thì dữ liệu nằm trong /tmp (RAM) và mất khi instance khởi động lại. ADR-0003."
  type        = bool
  default     = false
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
