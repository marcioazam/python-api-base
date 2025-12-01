# AWS VPC Module

Creates a VPC with public and private subnets, NAT Gateways, and route tables.

## Features

- VPC with DNS support enabled
- Public subnets with Internet Gateway
- Private subnets with NAT Gateway(s)
- Configurable single NAT Gateway for cost optimization
- Automatic CIDR subnet calculation

## Usage

```hcl
module "vpc" {
  source = "./modules/aws/vpc"

  name_prefix        = "my-app-prod"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  single_nat_gateway = false  # Use true for dev/staging to save costs
  
  tags = {
    Environment = "prod"
    Project     = "my-app"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| name_prefix | Prefix for resource names | `string` | n/a | yes |
| vpc_cidr | CIDR block for the VPC | `string` | `"10.0.0.0/16"` | no |
| availability_zones | List of AZs for subnet distribution | `list(string)` | `["us-east-1a", "us-east-1b", "us-east-1c"]` | no |
| single_nat_gateway | Use single NAT Gateway (cost optimization) | `bool` | `false` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | ID of the VPC |
| vpc_cidr_block | CIDR block of the VPC |
| public_subnet_ids | List of public subnet IDs |
| private_subnet_ids | List of private subnet IDs |
| nat_gateway_ids | List of NAT Gateway IDs |
| internet_gateway_id | ID of the Internet Gateway |

## Cost Optimization

Set `single_nat_gateway = true` for non-production environments to use a single NAT Gateway instead of one per AZ. This can save ~$100/month per additional NAT Gateway.

**Production**: Use `single_nat_gateway = false` for high availability.
