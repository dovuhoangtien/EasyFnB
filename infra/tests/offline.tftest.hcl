# Chạy: terraform test   (không cần tài khoản Google, dùng provider giả)
mock_provider "google" {}
mock_provider "random" {}

variables {
  project_id = "easy-fnb-test"
}

run "mac_dinh_khong_co_khoa_llm" {
  command = plan

  assert {
    condition     = length(google_secret_manager_secret.gemini) == 0 && length(google_secret_manager_secret.kie) == 0
    error_message = "Không có khoá thì không được tạo secret LLM."
  }

  assert {
    condition     = google_cloud_run_v2_service.app.template[0].scaling[0].max_instance_count == 1
    error_message = "Phải giữ đúng một instance (ADR-0003)."
  }

  assert {
    condition     = length(google_storage_bucket.data) == 1
    error_message = "Mặc định phải có bucket dữ liệu."
  }

  assert {
    condition     = length(google_billing_budget.month) == 0 && length(google_monitoring_alert_policy.down) == 0
    error_message = "Không có billing_account / alert_email thì bỏ budget và cảnh báo."
  }
}

run "co_khoa_gemini_va_cac_tuy_chon" {
  command = plan

  variables {
    gemini_api_key   = "khoa-gia"
    persist_data     = false
    alert_email      = "a@example.com"
    billing_account  = "000000-000000-000000"
    enable_vertex_ai = true
  }

  assert {
    condition     = length(google_secret_manager_secret.gemini) == 1 && length(google_secret_manager_secret.kie) == 0
    error_message = "Chỉ secret Gemini được tạo."
  }

  assert {
    condition     = length(google_storage_bucket.data) == 0
    error_message = "persist_data = false thì không có bucket dữ liệu."
  }

  assert {
    condition     = length(google_billing_budget.month) == 1 && length(google_monitoring_uptime_check_config.health) == 1
    error_message = "Phải có budget và uptime check."
  }

  assert {
    condition     = length(google_project_iam_member.run_vertex) == 1
    error_message = "enable_vertex_ai phải cấp aiplatform.user."
  }
}

run "tu_choi_nhieu_instance" {
  command = plan

  variables {
    min_instances = 2
  }

  expect_failures = [var.min_instances]
}
