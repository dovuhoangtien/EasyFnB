terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State chứa EDGE_KEY và khoá LLM (nếu truyền vào). Với dự án thật hãy bỏ chú thích khối này
  # (xem backend.tf.example) để state nằm trong bucket riêng, không nằm trên laptop.
}

provider "google" {
  project = var.project_id
  region  = var.region

  # Budget và một số API cần tính quota vào project của mình thay vì project của gcloud.
  user_project_override = true
  billing_project       = var.project_id
}
