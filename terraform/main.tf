# Terraform Configuration for my-api
# Multi-cloud infrastructure provisioning

# Backend configuration is provided via -backend-config flag or backend.hcl file
# See backend.hcl.example for required parameters
terraform {
  backend "s3" {
    encrypt = true
  }
}

# Local values
locals {
  common_tags = {
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "terraform"
  }
  
  name_prefix = "${var.app_name}-${var.environment}"
}
