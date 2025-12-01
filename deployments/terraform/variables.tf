# Terraform Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "cloud_provider" {
  description = "Cloud provider (aws, gcp, azure)"
  type        = string
  default     = "aws"

  validation {
    condition     = contains(["aws", "gcp", "azure"], var.cloud_provider)
    error_message = "Cloud provider must be aws, gcp, or azure."
  }
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "us-east-1"

  validation {
    condition = can(regex("^(us|eu|ap|sa|ca|me|af)-(east|west|north|south|central|northeast|southeast|southwest)-[1-9]$", var.region)) || can(regex("^(eastus|westus|northeurope|westeurope|eastus2|westus2|centralus|southcentralus|northcentralus|eastasia|southeastasia|japaneast|japanwest|australiaeast|australiasoutheast|brazilsouth|canadacentral|canadaeast|uksouth|ukwest|francecentral|germanywestcentral|norwayeast|switzerlandnorth)$", var.region))
    error_message = "Region must be a valid AWS region (e.g., us-east-1) or Azure region (e.g., eastus)."
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "my-api"
}

variable "db_instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "k8s_node_count" {
  description = "Number of Kubernetes nodes"
  type        = number
  default     = 3

  validation {
    condition     = var.k8s_node_count >= 1 && var.k8s_node_count <= 10
    error_message = "Node count must be between 1 and 10."
  }
}

variable "k8s_node_size" {
  description = "Kubernetes node size"
  type        = string
  default     = "t3.medium"
}

# GCP specific
variable "gcp_project_id" {
  description = "GCP Project ID (required when cloud_provider is gcp)"
  type        = string
  default     = ""

  validation {
    condition     = var.gcp_project_id != "" || var.cloud_provider != "gcp"
    error_message = "gcp_project_id is required when cloud_provider is gcp."
  }
}

# Azure specific
variable "azure_subscription_id" {
  description = "Azure Subscription ID (required when cloud_provider is azure)"
  type        = string
  default     = ""

  validation {
    condition     = var.azure_subscription_id != "" || var.cloud_provider != "azure"
    error_message = "azure_subscription_id is required when cloud_provider is azure."
  }
}

variable "azure_tenant_id" {
  description = "Azure Tenant ID (required when cloud_provider is azure)"
  type        = string
  default     = ""

  validation {
    condition     = var.azure_tenant_id != "" || var.cloud_provider != "azure"
    error_message = "azure_tenant_id is required when cloud_provider is azure."
  }
}

# Secrets Management
variable "use_secrets_manager" {
  description = "Use cloud secrets manager (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) instead of variables"
  type        = bool
  default     = true

  validation {
    condition     = var.use_secrets_manager == true || var.environment == "dev"
    error_message = "Secrets Manager must be enabled for non-dev environments."
  }
}

# Database credentials (sensitive) - DEPRECATED: Use Secrets Manager instead
variable "db_username" {
  description = "Database admin username (DEPRECATED: Use Secrets Manager in production)"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.use_secrets_manager || can(regex("^[a-zA-Z][a-zA-Z0-9_]{2,15}$", var.db_username))
    error_message = "Username must start with letter, 3-16 chars, alphanumeric and underscore only."
  }
}

variable "db_password" {
  description = "Database admin password (DEPRECATED: Use Secrets Manager in production)"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.use_secrets_manager || length(var.db_password) >= 8
    error_message = "Password must be at least 8 characters."
  }
}

# Deployment
variable "image_tag" {
  description = "Container image tag for deployment"
  type        = string

  validation {
    condition     = var.image_tag != "latest" && length(var.image_tag) > 0
    error_message = "image_tag is required and cannot be 'latest'. Use a specific version tag."
  }
}

# Cost optimization
variable "single_nat_gateway" {
  description = "Use a single NAT Gateway instead of one per AZ (cost optimization for non-prod)"
  type        = bool
  default     = false
}
