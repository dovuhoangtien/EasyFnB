data "google_project" "this" {
  project_id = var.project_id
}

locals {
  apis = concat(
    [
      "run.googleapis.com",
      "cloudbuild.googleapis.com",
      "artifactregistry.googleapis.com",
      "secretmanager.googleapis.com",
      "iam.googleapis.com",
      "cloudresourcemanager.googleapis.com",
      "serviceusage.googleapis.com",
      "monitoring.googleapis.com",
      "texttospeech.googleapis.com",
      "generativelanguage.googleapis.com",
    ],
    var.enable_vertex_ai ? ["aiplatform.googleapis.com"] : [],
    var.billing_account != "" ? ["billingbudgets.googleapis.com"] : [],
  )

  # nonsensitive: chỉ lấy "có khoá hay không", không lộ giá trị khoá.
  use_gemini = nonsensitive(var.gemini_api_key != "")
  use_kie    = nonsensitive(var.kie_api_key != "")
  backup     = var.backup_data && !var.persist_data

  image_repo = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}/${var.service_name}"
  data_mount = "/data"
}

resource "google_project_service" "api" {
  for_each = toset(local.apis)

  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------- tài khoản dịch vụ
resource "google_service_account" "run" {
  account_id   = "${var.service_name}-run"
  display_name = "Easy FnB (Cloud Run runtime)"

  depends_on = [google_project_service.api]
}

resource "google_service_account" "build" {
  account_id   = "${var.service_name}-build"
  display_name = "Easy FnB (Cloud Build)"

  depends_on = [google_project_service.api]
}

resource "google_project_iam_member" "run_vertex" {
  count = var.enable_vertex_ai ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.run.member
}

# ---------------------------------------------------------------- Artifact Registry và build
resource "google_artifact_registry_repository" "app" {
  repository_id = var.service_name
  location      = var.region
  format        = "DOCKER"
  description   = "Image của Easy FnB"

  # Giữ 10 image gần nhất, đủ để quay lại bản cũ khi demo hỏng.
  cleanup_policies {
    id     = "giu-10-ban-moi"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
  cleanup_policies {
    id     = "xoa-ban-cu"
    action = "DELETE"
    condition {
      older_than = "2592000s"
    }
  }

  depends_on = [google_project_service.api]
}

resource "google_storage_bucket" "build_src" {
  name                        = "${var.project_id}-${var.service_name}-build-src"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.api]
}

resource "google_storage_bucket_iam_member" "build_reads_src" {
  bucket = google_storage_bucket.build_src.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.build.member
}

resource "google_project_iam_member" "build_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.build.member
}

resource "google_artifact_registry_repository_iam_member" "build_pushes" {
  location   = google_artifact_registry_repository.app.location
  repository = google_artifact_registry_repository.app.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.build.member
}

resource "google_cloud_run_v2_service_iam_member" "build_deploys" {
  location = google_cloud_run_v2_service.app.location
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.developer"
  member   = google_service_account.build.member
}

# Build SA phải được phép "đóng vai" SA chạy app khi cập nhật revision.
resource "google_service_account_iam_member" "build_acts_as_run" {
  service_account_id = google_service_account.run.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.build.member
}

# ---------------------------------------------------------------- bí mật
resource "random_password" "edge_key" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret" "edge_key" {
  secret_id = "${var.service_name}-edge-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.api]
}

resource "google_secret_manager_secret_version" "edge_key" {
  secret      = google_secret_manager_secret.edge_key.id
  secret_data = random_password.edge_key.result
}

resource "google_secret_manager_secret_iam_member" "run_reads_edge_key" {
  secret_id = google_secret_manager_secret.edge_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.run.member
}

resource "google_secret_manager_secret" "gemini" {
  count = local.use_gemini ? 1 : 0

  secret_id = "${var.service_name}-gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.api]
}

resource "google_secret_manager_secret_version" "gemini" {
  count = local.use_gemini ? 1 : 0

  secret      = google_secret_manager_secret.gemini[0].id
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret_iam_member" "run_reads_gemini" {
  count = local.use_gemini ? 1 : 0

  secret_id = google_secret_manager_secret.gemini[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.run.member
}

resource "google_secret_manager_secret" "kie" {
  count = local.use_kie ? 1 : 0

  secret_id = "${var.service_name}-kie-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.api]
}

resource "google_secret_manager_secret_version" "kie" {
  count = local.use_kie ? 1 : 0

  secret      = google_secret_manager_secret.kie[0].id
  secret_data = var.kie_api_key
}

resource "google_secret_manager_secret_iam_member" "run_reads_kie" {
  count = local.use_kie ? 1 : 0

  secret_id = google_secret_manager_secret.kie[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.run.member
}

# ---------------------------------------------------------------- bucket dữ liệu (tùy chọn)
resource "google_storage_bucket" "data" {
  count = var.persist_data ? 1 : 0

  name                        = "${var.project_id}-${var.service_name}-data"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = var.data_retention_days
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.api]
}

resource "google_storage_bucket_iam_member" "run_writes_data" {
  count = var.persist_data ? 1 : 0

  bucket = google_storage_bucket.data[0].name
  role   = "roles/storage.objectUser"
  member = google_service_account.run.member
}

# ---------------------------------------------------------------- bucket sao lưu (Litestream)
# DATA_DIR vẫn ở /tmp; easy-fnb/deploy/start.sh khôi phục từ bucket khi khởi động và sao lưu liên tục.
resource "google_storage_bucket" "backup" {
  count = local.backup ? 1 : 0

  name                        = "${var.project_id}-${var.service_name}-backup"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  depends_on = [google_project_service.api]
}

resource "google_storage_bucket_iam_member" "run_writes_backup" {
  count = local.backup ? 1 : 0

  bucket = google_storage_bucket.backup[0].name
  role   = "roles/storage.objectAdmin" # Litestream cần xoá bản snapshot cũ
  member = google_service_account.run.member
}

# ---------------------------------------------------------------- Cloud Run
resource "google_cloud_run_v2_service" "app" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.run.email

    # SSE (/api/stream) và MJPEG giữ kết nối lâu; hết giờ thì trình duyệt tự nối lại.
    timeout = "3600s"

    # Gắn bucket Cloud Storage (FUSE) cần gen2.
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    # Một instance gánh cả luồng SSE, MJPEG và WebSocket nên nâng trần từ mặc định 80.
    max_instance_request_concurrency = 200

    # Một instance duy nhất: việc và trạng thái bàn nằm trong bộ nhớ (ADR-0003).
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = 1
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        # Luôn có CPU để bộ đếm chuyển việc (hub.tick_forever) chạy cả khi không có request.
        cpu_idle          = false
        startup_cpu_boost = true
      }

      env {
        name = "EDGE_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.edge_key.secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = local.use_gemini ? [1] : []
        content {
          name = "GEMINI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gemini[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = local.use_kie ? [1] : []
        content {
          name = "KIE_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.kie[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.persist_data ? [1] : []
        content {
          name  = "DATA_DIR"
          value = local.data_mount
        }
      }

      dynamic "env" {
        for_each = local.backup ? [1] : []
        content {
          name  = "BACKUP_BUCKET"
          value = google_storage_bucket.backup[0].name
        }
      }

      dynamic "env" {
        for_each = local.backup ? [1] : []
        content {
          name  = "BACKUP_PREFIX"
          value = var.backup_prefix
        }
      }

      # Không persist_data thì DATA_DIR là /tmp (RAM): giới hạn clip để không làm đầy bộ nhớ.
      env {
        name  = "CLIPS_MAX_MB"
        value = tostring(var.clips_max_mb)
      }

      # Giọng đọc cho điện thoại nhân viên: Google Cloud Text-to-Speech, xác thực bằng service account.
      env {
        name  = "TTS_ENGINE"
        value = "google"
      }

      # Bản demo tự chạy: clip che mặt làm hình camera, việc và nhân viên ảo (server/phat_demo.py).
      env {
        name  = "DEMO_FEED"
        value = var.demo_feed ? "1" : "0"
      }

      env {
        name  = "GOOGLE_TTS_VOICE"
        value = var.tts_voice
      }

      dynamic "env" {
        for_each = var.gemini_model != "" ? [1] : []
        content {
          name  = "GEMINI_MODEL"
          value = var.gemini_model
        }
      }

      dynamic "env" {
        for_each = var.gemini_verify_model != "" ? [1] : []
        content {
          name  = "GEMINI_VERIFY_MODEL"
          value = var.gemini_verify_model
        }
      }

      dynamic "volume_mounts" {
        for_each = var.persist_data ? [1] : []
        content {
          name       = "du-lieu"
          mount_path = local.data_mount
        }
      }
    }

    dynamic "volumes" {
      for_each = var.persist_data ? [1] : []
      content {
        name = "du-lieu"
        gcs {
          bucket    = google_storage_bucket.data[0].name
          read_only = false
        }
      }
    }
  }

  # Cloud Build (infra/cloudbuild.yaml) đổi image ở mỗi lần deploy; Terraform không kéo về lại image khởi tạo.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.api,
    google_secret_manager_secret_version.edge_key,
    google_secret_manager_secret_iam_member.run_reads_edge_key,
    google_secret_manager_secret_version.gemini,
    google_secret_manager_secret_iam_member.run_reads_gemini,
    google_secret_manager_secret_version.kie,
    google_secret_manager_secret_iam_member.run_reads_kie,
    google_storage_bucket_iam_member.run_writes_data,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.app.location
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
