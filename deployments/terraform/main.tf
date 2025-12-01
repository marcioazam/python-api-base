# Terraform Configuration for my-api
# Multi-cloud infrastructure provisioning

# Backend configuration is provided via -backend-config flag or backend.hcl file
# See backend.hcl.example for required parameters
# Workspace is automatically appended to key path for environment isolation
terraform {
  backend "s3" {
    encrypt        = true
    dynamodb_table = "my-api-terraform-locks"
    # Key will be: my-api/${terraform.workspace}/terraform.tfstate
    # Configured via backend.hcl
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
