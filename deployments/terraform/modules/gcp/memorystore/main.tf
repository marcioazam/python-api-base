# GCP Memorystore Redis Module

variable "project_id" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "region" {
  type = string
}

variable "network_id" {
  type = string
}

variable "tier" {
  type    = string
  default = "BASIC"
}

variable "memory_size_gb" {
  type    = number
  default = 1
}

variable "redis_version" {
  type    = string
  default = "REDIS_7_0"
}

variable "labels" {
  type    = map(string)
  default = {}
}

# Random auth string
resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# Secret Manager
resource "google_secret_manager_secret" "redis_auth" {
  project   = var.project_id
  secret_id = "${var.name_prefix}-redis-auth"

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "redis_auth" {
  secret = google_secret_manager_secret.redis_auth.id
  secret_data = jsonencode({
    auth_string = random_password.redis_auth.result
    host        = google_redis_instance.main.host
    port        = google_redis_instance.main.port
  })
}

# Redis Instance
resource "google_redis_instance" "main" {
  project        = var.project_id
  name           = "${var.name_prefix}-redis"
  region         = var.region
  tier           = var.tier
  memory_size_gb = var.memory_size_gb
  redis_version  = var.redis_version

  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  maintenance_policy {
    weekly_maintenance_window {
      day = "MONDAY"
      start_time {
        hours   = 4
        minutes = 0
      }
    }
  }

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }

  labels = var.labels
}

# Outputs
output "endpoint" {
  value = google_redis_instance.main.host
}

output "port" {
  value = google_redis_instance.main.port
}

output "secret_id" {
  value = google_secret_manager_secret.redis_auth.secret_id
}
