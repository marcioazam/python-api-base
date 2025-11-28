# Terraform Outputs

output "environment" {
  description = "Deployed environment"
  value       = var.environment
}

output "cloud_provider" {
  description = "Cloud provider used"
  value       = var.cloud_provider
}

output "region" {
  description = "Deployment region"
  value       = var.region
}

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

output "kubernetes_cluster_name" {
  description = "Kubernetes cluster name"
  value       = var.cloud_provider == "aws" ? module.aws_eks[0].cluster_name : (
                var.cloud_provider == "gcp" ? module.gcp_gke[0].cluster_name : 
                module.azure_aks[0].cluster_name)
}
