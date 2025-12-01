# Deployments

Configurações de deploy production-ready para `my-api` em múltiplos ambientes e clouds.

## 📁 Estrutura

```
deployments/
├── docker/               # Docker Compose para local/dev
├── helm/                # Helm charts para Kubernetes
│   └── api/            # Chart principal da API
├── k8s/                # Kubernetes manifests base
│   ├── base/           # Manifests compartilhados
│   ├── api/            # API específicos
│   ├── jobs/           # CronJobs e Jobs
│   ├── monitoring/     # Prometheus, Grafana
│   ├── tracing/        # Jaeger/OpenTelemetry
│   └── worker/         # Workers/Background jobs
└── terraform/          # Infrastructure as Code
    ├── modules/        # Módulos reutilizáveis
    └── environments/   # Configs por ambiente
```

## 🚀 Quick Start

### Local Development (Docker Compose)

```bash
# Dev environment
docker-compose -f deployments/docker/docker-compose.yml up

# Production simulation
docker-compose -f deployments/docker/docker-compose.prod.yml up
```

### Kubernetes (Helm)

```bash
# Add dependencies
helm dependency update deployments/helm/api/

# Install
helm install my-api deployments/helm/api/ \
  --namespace my-api \
  --create-namespace \
  --values deployments/helm/api/values.yaml \
  --set image.tag=v1.0.0

# Upgrade
helm upgrade my-api deployments/helm/api/ \
  --namespace my-api \
  --values deployments/helm/api/values.yaml \
  --set image.tag=v1.1.0
```

### Infrastructure (Terraform)

```bash
cd deployments/terraform

# Initialize with workspace
terraform workspace new prod
terraform init -backend-config=backend.hcl

# Plan
terraform plan -var-file=environments/prod.tfvars

# Apply
terraform apply -var-file=environments/prod.tfvars
```

## 🔐 Security Best Practices

### ✅ Implemented

1. **External Secrets Operator** - Secrets nunca em Git
2. **Redis Authentication** - Auth habilitado por padrão
3. **AWS Secrets Manager Integration** - DB credentials seguros
4. **Network Policies** - Ingress/Egress restrito
5. **Security Contexts** - runAsNonRoot, readOnlyRootFilesystem
6. **Image Tag Validation** - Sem `latest` em produção
7. **RBAC** - Least privilege principle
8. **Resource Quotas** - Previne resource exhaustion

### 🔴 CRITICAL: Antes do Deploy em Produção

#### 1. Configure External Secrets

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# Create SecretStore (AWS example)
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets-system
EOF
```

#### 2. Create Secrets in AWS Secrets Manager

```bash
# Database credentials
aws secretsmanager create-secret \
  --name my-api/prod/db-credentials \
  --secret-string '{"username":"myapi_admin","password":"STRONG-PASSWORD-HERE"}'

# Application secrets
aws secretsmanager create-secret \
  --name my-api/prod/database-url \
  --secret-string "postgresql://user:pass@host:5432/db"

aws secretsmanager create-secret \
  --name my-api/prod/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name my-api/prod/redis-password \
  --secret-string "$(openssl rand -base64 24)"
```

#### 3. Enable External Secrets in Helm

```yaml
# values-prod.yaml
externalSecrets:
  enabled: true  # ← MUST BE TRUE
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
```

#### 4. Deploy with External Secrets

```bash
helm upgrade --install my-api deployments/helm/api/ \
  --namespace my-api \
  --values deployments/helm/api/values.yaml \
  --values values-prod.yaml \
  --set image.tag=v1.0.0
```

## ⚡ Performance Optimizations

### Vertical Pod Autoscaler (VPA)

Automatic resource rightsizing based on actual usage:

```bash
# Install VPA (if not already installed)
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vertical-pod-autoscaler.yaml

# Deploy VPA for my-api
kubectl apply -f deployments/k8s/base/vpa.yaml
```

### Horizontal Pod Autoscaler (HPA)

Already configured in Helm chart (enabled by default):

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### DNS Caching

Configured in deployment template to reduce DNS lookup latency:

```yaml
dnsConfig:
  options:
    - name: ndots
      value: "1"      # Reduce DNS queries
    - name: timeout
      value: "2"      # Faster timeout
    - name: attempts
      value: "2"      # Fewer retries
```

## 💰 Cost Optimization

### Spot Instances (Terraform)

```hcl
# terraform/modules/aws/eks/main.tf
# Spot instances are ~70% cheaper than On-Demand

# Enable in your tfvars:
# enable_spot = true
# spot_node_count = 3
```

### Single NAT Gateway (Non-Prod)

```hcl
# Saves $45/month per NAT gateway
# terraform.tfvars
single_nat_gateway = true  # Dev/Staging only
```

### Resource Quotas

Prevents runaway costs from over-provisioning:

```bash
kubectl apply -f deployments/k8s/base/resourcequota.yaml
```

## 📊 Observability

### Prometheus Metrics

ServiceMonitor enabled by default:

```yaml
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
```

Access metrics:

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090
```

### Health Checks

Three-tiered health check strategy:

1. **startupProbe** - Initial startup (60s max)
2. **livenessProbe** - Container health (restart if fails)
3. **readinessProbe** - Traffic routing (remove from service if fails)

## 🔄 CI/CD Integration

### GitHub Actions Workflows

Automated validation on every PR:

- `.github/workflows/terraform.yml` - Terraform fmt/validate/plan
- `.github/workflows/helm.yml` - Helm lint/test/package

### Pre-Deployment Checklist

```bash
# 1. Validate Helm chart
helm lint deployments/helm/api/

# 2. Validate Kubernetes manifests
kubectl apply --dry-run=client -f deployments/k8s/base/

# 3. Validate Terraform
cd deployments/terraform
terraform fmt -check -recursive
terraform validate

# 4. Security scan
trivy config deployments/

# 5. Test Helm install (kind cluster)
kind create cluster --name test
helm install test deployments/helm/api/ \
  --set postgresql.enabled=false \
  --set redis.enabled=false
helm test test
```

## 🏗️ Multi-Cloud Support

### AWS

```bash
terraform apply \
  -var="cloud_provider=aws" \
  -var="region=us-east-1" \
  -var-file=environments/prod.tfvars
```

### GCP

```bash
terraform apply \
  -var="cloud_provider=gcp" \
  -var="gcp_project_id=my-project" \
  -var="region=us-central1" \
  -var-file=environments/prod.tfvars
```

### Azure

```bash
terraform apply \
  -var="cloud_provider=azure" \
  -var="azure_subscription_id=xxx" \
  -var="azure_tenant_id=yyy" \
  -var="region=eastus" \
  -var-file=environments/prod.tfvars
```

## 🆘 Troubleshooting

### Common Issues

#### 1. External Secrets not syncing

```bash
# Check SecretStore
kubectl get clustersecretstore aws-secretsmanager -o yaml

# Check ExternalSecret
kubectl get externalsecret -n my-api
kubectl describe externalsecret my-api-external -n my-api

# Check IRSA (AWS)
kubectl get sa -n my-api my-api -o yaml
```

#### 2. Pods stuck in Pending

```bash
# Check events
kubectl describe pod -n my-api <pod-name>

# Check resource quotas
kubectl get resourcequota -n my-api
kubectl describe resourcequota my-api-quota -n my-api

# Check PVC
kubectl get pvc -n my-api
```

#### 3. VPA not updating resources

```bash
# Check VPA recommendations
kubectl get vpa my-api-vpa -n my-api -o yaml

# Check VPA controller logs
kubectl logs -n kube-system -l app=vpa-updater
```

#### 4. Terraform state locked

```bash
# Force unlock (use with caution!)
terraform force-unlock <LOCK_ID>

# Check DynamoDB lock table
aws dynamodb scan --table-name my-api-terraform-locks
```

## 📚 Additional Resources

- [Helm Chart Documentation](./helm/api/README.md)
- [Terraform Modules](./terraform/README.md)
- [ADR-014: Deployment Optimizations](../docs/architecture/adr/ADR-014-deployment-optimizations.md)
- [External Secrets Operator](https://external-secrets.io/)
- [Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

## 🔖 Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Kubernetes | 1.28+ | Tested on 1.28, 1.29 |
| Helm | 3.14+ | Chart API v2 |
| Terraform | 1.6+ | Using new validation |
| External Secrets | 0.9+ | ClusterSecretStore |
| PostgreSQL | 16 | Bitnami chart 12.12+ |
| Redis | 7 | Bitnami chart 17.17+ |

## ⚠️ Known Limitations

1. **Terraform Workspaces** - State key must be configured manually in backend.hcl
2. **Multi-Cloud** - Only one cloud provider per Terraform apply
3. **VPA** - Requires separate installation, not included in Helm chart
4. **Spot Instances** - Not suitable for stateful workloads

## 🤝 Contributing

When modifying deployments:

1. Update relevant documentation
2. Run validation locally
3. Test in dev environment first
4. Update ADR if architecture changes
5. Ensure CI passes before merge

---

**Last Updated**: 2025-12-01
**Maintainer**: API Team (api-team@example.com)
