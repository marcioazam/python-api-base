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

## Security

### Sensitive Variables

The following variables contain sensitive data and should be provided via environment variables or a secure secrets manager:

| Variable | Description | Required |
|----------|-------------|----------|
| `db_username` | Database admin username | Yes |
| `db_password` | Database admin password | Yes |
| `image_tag` | Container image tag (cannot be "latest") | Yes |

**Never commit sensitive values to version control.**

### Environment Variables

```bash
# Set sensitive variables via environment
export TF_VAR_db_username="myapi_admin"
export TF_VAR_db_password="secure-password-here"
export TF_VAR_image_tag="v1.2.3"
```

## Backend Configuration

State is stored in S3 with DynamoDB locking. Backend configuration is provided via partial configuration.

### Setup

1. Create the backend resources:

```bash
# Create state bucket
aws s3 mb s3://my-api-terraform-state-dev
aws s3api put-bucket-versioning --bucket my-api-terraform-state-dev --versioning-configuration Status=Enabled

# Create lock table
aws dynamodb create-table --table-name my-api-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

2. Copy and configure backend:

```bash
cp backend.hcl.example backend.hcl
# Edit backend.hcl with your values
```

3. Initialize with backend config:

```bash
terraform init -backend-config=backend.hcl
```

## Usage

```bash
# Initialize
terraform init -backend-config=backend.hcl

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

## Cost Optimization

### NAT Gateway

Set `single_nat_gateway = true` in non-production environments to use a single NAT Gateway instead of one per AZ.

| Environment | single_nat_gateway | NAT Gateways | Monthly Cost (approx) |
|-------------|-------------------|--------------|----------------------|
| dev | true | 1 | ~$45 |
| staging | true | 1 | ~$45 |
| prod | false | 3 | ~$135 |

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

## File Structure

```
terraform/
├── main.tf              # Backend configuration
├── versions.tf          # Provider version constraints
├── providers.tf         # Provider configurations
├── variables.tf         # All input variables
├── outputs.tf           # All outputs
├── aws.tf               # AWS resources
├── azure.tf             # Azure resources
├── gcp.tf               # GCP resources
├── backend.hcl.example  # Backend config template
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
└── modules/
    ├── aws/
    ├── azure/
    └── gcp/
```

## Troubleshooting

### Backend Initialization Errors

```
Error: Backend configuration changed
```

Solution: Run `terraform init -reconfigure -backend-config=backend.hcl`

### Provider Authentication

**AWS**: Ensure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set, or use `aws configure`.

**GCP**: Run `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS`.

**Azure**: Run `az login` or set service principal credentials.

### Validation Errors

```
Error: Invalid value for variable
```

Check that:
- `region` is a valid AWS/Azure region
- `gcp_project_id` is set when `cloud_provider = "gcp"`
- `azure_subscription_id` and `azure_tenant_id` are set when `cloud_provider = "azure"`
- `image_tag` is not "latest"
