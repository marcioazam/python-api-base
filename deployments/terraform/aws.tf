# AWS Resources and Module Calls

# Fetch secrets from AWS Secrets Manager (more secure than variables)
data "aws_secretsmanager_secret" "db_credentials" {
  count = var.cloud_provider == "aws" && var.use_secrets_manager ? 1 : 0
  name  = "my-api/${var.environment}/db-credentials"
}

data "aws_secretsmanager_secret_version" "db_credentials" {
  count     = var.cloud_provider == "aws" && var.use_secrets_manager ? 1 : 0
  secret_id = data.aws_secretsmanager_secret.db_credentials[0].id
}

locals {
  db_credentials = var.use_secrets_manager ? jsondecode(data.aws_secretsmanager_secret_version.db_credentials[0].secret_string) : {
    username = var.db_username
    password = var.db_password
  }
}

# VPC Module
module "aws_vpc" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  source = "./modules/aws/vpc"

  name_prefix        = local.name_prefix
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["${var.region}a", "${var.region}b", "${var.region}c"]
  single_nat_gateway = var.single_nat_gateway
  tags               = local.common_tags
}

# RDS Module
module "aws_database" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  source = "./modules/aws/rds"

  name_prefix           = local.name_prefix
  vpc_id                = module.aws_vpc[0].vpc_id
  subnet_ids            = module.aws_vpc[0].private_subnet_ids
  instance_class        = var.db_instance_class
  allocated_storage     = 20
  max_allocated_storage = 100
  db_name               = "myapi"
  db_username           = local.db_credentials.username
  db_password           = local.db_credentials.password
  multi_az              = var.environment == "prod"
  backup_retention_period = var.environment == "prod" ? 30 : 7
  tags                  = local.common_tags
}

# ElastiCache Module
module "aws_redis" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  source = "./modules/aws/elasticache"

  name_prefix     = local.name_prefix
  vpc_id          = module.aws_vpc[0].vpc_id
  subnet_ids      = module.aws_vpc[0].private_subnet_ids
  node_type       = var.redis_node_type
  num_cache_nodes = var.environment == "prod" ? 3 : 1
  tags            = local.common_tags
}

# EKS Module
module "aws_eks" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  source = "./modules/aws/eks"

  name_prefix        = local.name_prefix
  vpc_id             = module.aws_vpc[0].vpc_id
  subnet_ids         = module.aws_vpc[0].private_subnet_ids
  node_count         = var.k8s_node_count
  node_instance_type = var.k8s_node_size
  kubernetes_version = "1.28"
  tags               = local.common_tags
}

# Deploy Application via Helm
resource "helm_release" "my_api" {
  count = var.cloud_provider == "aws" ? 1 : 0

  name       = var.app_name
  chart      = "../helm/my-api"
  namespace  = "default"

  values = [
    yamlencode({
      replicaCount = var.environment == "prod" ? 3 : 1
      
      image = {
        repository = "ghcr.io/myorg/my-api"
        tag        = var.image_tag
      }

      postgresql = {
        enabled = false
        external = {
          host     = module.aws_database[0].address
          port     = 5432
          database = "myapi"
        }
      }

      redis = {
        enabled = false
        external = {
          host = module.aws_redis[0].endpoint
          port = 6379
        }
      }

      ingress = {
        enabled = true
        className = "nginx"
        hosts = [{
          host = "${var.app_name}.${var.environment}.example.com"
          paths = [{
            path = "/"
            pathType = "Prefix"
          }]
        }]
      }

      resources = {
        limits = {
          cpu    = var.environment == "prod" ? "1000m" : "500m"
          memory = var.environment == "prod" ? "1Gi" : "512Mi"
        }
        requests = {
          cpu    = var.environment == "prod" ? "500m" : "250m"
          memory = var.environment == "prod" ? "512Mi" : "256Mi"
        }
      }

      autoscaling = {
        enabled     = var.environment == "prod"
        minReplicas = 3
        maxReplicas = 10
      }
    })
  ]

  depends_on = [module.aws_eks]
}
