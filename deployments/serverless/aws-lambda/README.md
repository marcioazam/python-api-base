# AWS Lambda Deployment

Deploy the Python API Base to AWS Lambda using SAM (Serverless Application Model).

## Prerequisites

- AWS CLI configured
- AWS SAM CLI installed
- Python 3.12+

## Quick Start

```bash
# Build
sam build --template deployments/serverless/aws-lambda/template.yaml

# Deploy (guided)
sam deploy --guided

# Deploy (with parameters)
sam deploy \
  --stack-name python-api-base-dev \
  --parameter-overrides \
    Stage=dev \
    DatabaseUrl="postgresql://..." \
  --capabilities CAPABILITY_IAM
```

## Local Testing

```bash
# Start local API Gateway
sam local start-api --template deployments/serverless/aws-lambda/template.yaml

# Test single invocation
sam local invoke ApiFunction --event events/api-gateway.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ API Gateway (HTTP API v2)                                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Lambda Function                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Mangum Adapter                                          │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ FastAPI Application                                 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Cold Start Optimization

1. **Keep dependencies minimal** in Lambda layer
2. **Use provisioned concurrency** for production
3. **Lazy load** heavy modules (database connections, etc.)

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ENVIRONMENT` | Deployment environment | Yes |
| `DATABASE__URL` | PostgreSQL connection URL | Yes |
| `SECURITY__SECRET_KEY` | JWT signing key | Yes |
| `OBSERVABILITY__REDIS_URL` | Redis URL (optional) | No |

## Monitoring

- CloudWatch Logs: `/aws/lambda/python-api-base-{stage}`
- X-Ray tracing enabled by default
- Custom metrics via AWS Lambda Powertools
