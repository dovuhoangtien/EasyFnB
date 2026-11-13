locals {
  alerts_on = var.alert_email != ""
  host      = trimprefix(google_cloud_run_v2_service.app.uri, "https://")
}

resource "google_monitoring_notification_channel" "email" {
  count = local.alerts_on ? 1 : 0

  display_name = "Easy FnB: ${var.alert_email}"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }

  depends_on = [google_project_service.api]
}

# /api/health không đụng tới AI hay ổ đĩa, chỉ cho biết tiến trình còn sống.
resource "google_monitoring_uptime_check_config" "health" {
  count = local.alerts_on ? 1 : 0

  display_name = "${var.service_name} /api/health"
  timeout      = "10s"
  period       = "300s"

  http_check {
    path         = "/api/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.host
    }
  }

  depends_on = [google_project_service.api]
}

resource "google_monitoring_alert_policy" "down" {
  count = local.alerts_on ? 1 : 0

  display_name = "${var.service_name} không phản hồi"
  combiner     = "OR"

  conditions {
    display_name = "Kiểm tra /api/health thất bại"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "metric.label.check_id=\"${google_monitoring_uptime_check_config.health[0].uptime_check_id}\"",
        "resource.type=\"uptime_url\"",
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.*"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email[0].id]
}

# ---------------------------------------------------------------- ngân sách
resource "google_billing_budget" "month" {
  count = var.billing_account != "" ? 1 : 0

  billing_account = var.billing_account
  display_name    = "${var.service_name} hằng tháng"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  dynamic "all_updates_rule" {
    for_each = local.alerts_on ? [1] : []
    content {
      monitoring_notification_channels = [google_monitoring_notification_channel.email[0].id]
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.api]
}
