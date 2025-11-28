# GCP Cloud SQL PostgreSQL Module

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
  default = "db-f1-micro"
}

variable "disk_size" {
  type    = number
  default = 20
}

variable "db_name" {
  type    = string
  default = "myapi"
}

variable "high_availability" {
  type    = bool
  default = false
}

variable "labels" {
  type    = map(string)
  default = {}
}

# Random password
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Secret Manager
resource "google_secret_manager_secret" "db_credentials" {
  project   = var.project_id
  secret_id = "${var.name_prefix}-db-credentials"

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "db_credentials" {
  secret = google_secret_manager_secret.db_credentials.id
  secret_data = jsonencode({
    username = "myapi_user"
    password = random_password.db_password.result
    host     = google_sql_database_instance.main.private_ip_address
    port     = 5432
    database = var.db_name
  })
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  project          = var.project_id
  name             = "${var.name_prefix}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.tier
    disk_size         = var.disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = var.high_availability ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }

    maintenance_window {
      day  = 1
      hour = 4
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }

    user_labels = var.labels
  }

  deletion_protection = true
}

# Database
resource "google_sql_database" "main" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

# User
resource "google_sql_user" "main" {
  project  = var.project_id
  name     = "myapi_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Outputs
output "endpoint" {
  value = google_sql_database_instance.main.private_ip_address
}

output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "secret_id" {
  value = google_secret_manager_secret.db_credentials.secret_id
}
