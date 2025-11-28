# Terraform Configuration for my-api
# Multi-cloud infrastructure provisioning

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket         = "my-api-terraform-state"
    key            = "state/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "my-api-terraform-locks"
  }
}

# Variables
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "cloud_provider" {
  description = "Cloud provider (aws, gcp, azure)"
  type        = string
  default     = "aws"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "us-east-1"
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
}

variable "k8s_node_size" {
  description = "Kubernetes node size"
  type        = string
  default     = "t3.medium"
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

# Outputs
output "database_endpoint" {
  description = "Database connection endpoint"
  value       = var.cloud_provider == "aws" ? module.aws_database[0].endpoint : (
                var.cloud_provider == "gcp" ? module.gcp_database[0].endpoint : 
                module.azure_database[0].endpoint)
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis connection endpoint"
  value       = var.cloud_provider == "aws" ? module.aws_redis[0].endpoint : (
                var.cloud_provider == "gcp" ? module.gcp_redis[0].endpoint : 
                module.azure_redis[0].endpoint)
  sensitive   = true
}

output "kubernetes_endpoint" {
  description = "Kubernetes API endpoint"
  value       = var.cloud_provider == "aws" ? module.aws_eks[0].endpoint : (
                var.cloud_provider == "gcp" ? module.gcp_gke[0].endpoint : 
                module.azure_aks[0].endpoint)
}
