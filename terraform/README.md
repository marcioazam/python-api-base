# Terraform Infrastructure

Multi-cloud infrastructure provisioning for my-api.

## Supported Providers

- AWS (EKS, RDS, ElastiCache)
- GCP (GKE, Cloud SQL, Memorystore)
- Azure (AKS, PostgreSQL Flexible Server, Redis Cache)

## Prerequisites

- Terraform >= 1.5.0
- Cloud provider CLI configured (aws, gcloud, az)
- kubectl

## Usage

```bash
# Initialize
terraform init

# Plan (dev)
terraform plan -var-file=environments/dev.tfvars

# Apply (dev)
terraform apply -var-file=environments/dev.tfvars

# Plan (prod)
terraform plan -var-file=environments/prod.tfvars

# Apply (prod)
terraform apply -var-file=environments/prod.tfvars
```

## Multi-Cloud

```bash
# AWS
terraform apply -var="cloud_provider=aws" -var-file=environments/dev.tfvars

# GCP
terraform apply -var="cloud_provider=gcp" -var="gcp_project_id=my-project" -var-file=environments/dev.tfvars

# Azure
terraform apply -var="cloud_provider=azure" -var="azure_subscription_id=xxx" -var="azure_tenant_id=yyy" -var-file=environments/dev.tfvars
```

## Modules

| Module | Description |
|--------|-------------|
| aws/vpc | VPC with public/private subnets |
| aws/rds | PostgreSQL RDS instance |
| aws/elasticache | Redis ElastiCache cluster |
| aws/eks | EKS Kubernetes cluster |
| gcp/cloudsql | Cloud SQL PostgreSQL |
| gcp/memorystore | Memorystore Redis |
| gcp/gke | GKE Kubernetes cluster |
| azure/postgresql | PostgreSQL Flexible Server |
| azure/redis | Azure Redis Cache |
| azure/aks | AKS Kubernetes cluster |

## State Management

State is stored in S3 with DynamoDB locking (AWS).

```bash
# Create state bucket
aws s3 mb s3://my-api-terraform-state
aws dynamodb create-table --table-name my-api-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```
