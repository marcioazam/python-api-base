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
  value = coalesce(
    try(module.aws_database[0].endpoint, null),
    try(module.gcp_database[0].endpoint, null),
    try(module.azure_database[0].endpoint, null)
  )
  sensitive = true
}

output "redis_endpoint" {
  description = "Redis connection endpoint"
  value = coalesce(
    try(module.aws_redis[0].endpoint, null),
    try(module.gcp_redis[0].endpoint, null),
    try(module.azure_redis[0].endpoint, null)
  )
  sensitive = true
}

output "kubernetes_endpoint" {
  description = "Kubernetes API endpoint"
  value = coalesce(
    try(module.aws_eks[0].endpoint, null),
    try(module.gcp_gke[0].endpoint, null),
    try(module.azure_aks[0].endpoint, null)
  )
}

output "kubernetes_cluster_name" {
  description = "Kubernetes cluster name"
  value = coalesce(
    try(module.aws_eks[0].cluster_name, null),
    try(module.gcp_gke[0].cluster_name, null),
    try(module.azure_aks[0].cluster_name, null)
  )
}
