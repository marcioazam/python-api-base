# GCP Provider Configuration and Module Calls

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = ""
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

# VPC Network
resource "google_compute_network" "main" {
  count                   = var.cloud_provider == "gcp" ? 1 : 0
  project                 = var.gcp_project_id
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  project       = var.gcp_project_id
  name          = "${local.name_prefix}-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.main[0].id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }

  private_ip_google_access = true
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  project       = var.gcp_project_id
  name          = "${local.name_prefix}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main[0].id
}

resource "google_service_networking_connection" "private_vpc" {
  count                   = var.cloud_provider == "gcp" ? 1 : 0
  network                 = google_compute_network.main[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip[0].name]
}

# Cloud SQL Module
module "gcp_database" {
  count  = var.cloud_provider == "gcp" ? 1 : 0
  source = "./modules/gcp/cloudsql"

  project_id        = var.gcp_project_id
  name_prefix       = local.name_prefix
  region            = var.region
  network_id        = google_compute_network.main[0].id
  tier              = var.db_instance_class == "db.t3.micro" ? "db-f1-micro" : "db-custom-2-4096"
  disk_size         = 20
  db_name           = "myapi"
  high_availability = var.environment == "prod"
  labels            = local.common_tags

  depends_on = [google_service_networking_connection.private_vpc]
}

# Memorystore Module
module "gcp_redis" {
  count  = var.cloud_provider == "gcp" ? 1 : 0
  source = "./modules/gcp/memorystore"

  project_id     = var.gcp_project_id
  name_prefix    = local.name_prefix
  region         = var.region
  network_id     = google_compute_network.main[0].id
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.environment == "prod" ? 5 : 1
  labels         = local.common_tags

  depends_on = [google_service_networking_connection.private_vpc]
}

# GKE Module
module "gcp_gke" {
  count  = var.cloud_provider == "gcp" ? 1 : 0
  source = "./modules/gcp/gke"

  project_id         = var.gcp_project_id
  name_prefix        = local.name_prefix
  region             = var.region
  network_id         = google_compute_network.main[0].id
  subnetwork_id      = google_compute_subnetwork.main[0].id
  node_count         = var.k8s_node_count
  machine_type       = var.k8s_node_size == "t3.medium" ? "e2-medium" : "e2-standard-2"
  kubernetes_version = "1.28"
  labels             = local.common_tags
}
