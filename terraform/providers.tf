# Terraform Providers Configuration
# Centralized provider configurations for multi-cloud support

# AWS Provider
provider "aws" {
  region = var.region

  default_tags {
    tags = local.common_tags
  }
}

# GCP Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

# Azure Provider
provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# Kubernetes Provider
# Uses try() for safe access when EKS module is not instantiated
provider "kubernetes" {
  host                   = try(module.aws_eks[0].endpoint, "")
  cluster_ca_certificate = try(base64decode(module.aws_eks[0].cluster_ca_certificate), "")

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", try(module.aws_eks[0].cluster_name, "")]
  }
}

# Helm Provider
# Uses try() for safe access when EKS module is not instantiated
provider "helm" {
  kubernetes {
    host                   = try(module.aws_eks[0].endpoint, "")
    cluster_ca_certificate = try(base64decode(module.aws_eks[0].cluster_ca_certificate), "")

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", try(module.aws_eks[0].cluster_name, "")]
    }
  }
}
