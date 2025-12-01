# my-api Helm Chart

A Helm chart for deploying the my-api Python FastAPI application on Kubernetes.

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8+
- PV provisioner support (if using PostgreSQL persistence)

## Installation

```bash
# Add Bitnami repository for dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install the chart
helm install my-api ./helm/my-api -n my-api --create-namespace

# Install with custom values
helm install my-api ./helm/my-api -n my-api --create-namespace -f custom-values.yaml
```

## Upgrading

```bash
helm upgrade my-api ./helm/my-api -n my-api
```

## Uninstallation

```bash
helm uninstall my-api -n my-api
```

## Configuration

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `3` |
| `nameOverride` | Override chart name | `""` |
| `fullnameOverride` | Override full name | `""` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `my-api` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `latest` |
| `imagePullSecrets` | Image pull secrets | `[]` |

### Service Account Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.annotations` | Service account annotations | `{}` |
| `serviceAccount.name` | Service account name | `""` |

### Security Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `podSecurityContext.fsGroup` | Pod filesystem group | `1000` |
| `securityContext.runAsNonRoot` | Run as non-root | `true` |
| `securityContext.runAsUser` | Run as user ID | `1000` |
| `securityContext.readOnlyRootFilesystem` | Read-only root filesystem | `true` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts` | Ingress hosts configuration | See values.yaml |
| `ingress.tls` | Ingress TLS configuration | See values.yaml |

### Resource Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `250m` |
| `resources.requests.memory` | Memory request | `256Mi` |

### Autoscaling Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `3` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `70` |
| `autoscaling.targetMemoryUtilizationPercentage` | Target memory utilization | `80` |

### Network Policy Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `networkPolicy.enabled` | Enable NetworkPolicy | `true` |
| `networkPolicy.ingressNamespace` | Allowed ingress namespace | `ingress-nginx` |

### RBAC Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rbac.create` | Create RBAC resources | `true` |

### Pod Disruption Budget Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `podDisruptionBudget.enabled` | Enable PDB | `true` |
| `podDisruptionBudget.minAvailable` | Minimum available pods | `1` |
| `podDisruptionBudget.maxUnavailable` | Maximum unavailable pods | `nil` |

### Metrics Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `metrics.enabled` | Enable metrics | `true` |
| `metrics.path` | Metrics path | `/metrics` |
| `metrics.serviceMonitor.enabled` | Enable ServiceMonitor | `false` |
| `metrics.serviceMonitor.interval` | Scrape interval | `30s` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.environment` | Environment name | `production` |
| `config.logLevel` | Log level | `INFO` |
| `config.corsOrigins` | CORS origins | `https://app.example.com` |
| `config.rateLimitRequests` | Rate limit requests | `100` |
| `config.rateLimitPeriod` | Rate limit period (seconds) | `60` |
| `config.cacheTtl` | Cache TTL (seconds) | `300` |

### Secrets Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.databaseUrl` | Database connection URL | `""` |
| `secrets.jwtSecret` | JWT signing secret | `""` |
| `secrets.redisUrl` | Redis connection URL | `""` |

### External Secrets Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `externalSecrets.enabled` | Use External Secrets Operator | `false` |
| `externalSecrets.secretStoreRef.name` | SecretStore name | `""` |
| `externalSecrets.secretStoreRef.kind` | SecretStore kind | `ClusterSecretStore` |
| `externalSecrets.refreshInterval` | Refresh interval | `1h` |

### PostgreSQL Subchart

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.database` | Database name | `myapi` |
| `postgresql.auth.username` | Database username | `myapi` |
| `postgresql.primary.persistence.size` | PVC size | `10Gi` |

### Redis Subchart

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.architecture` | Redis architecture | `standalone` |
| `redis.auth.enabled` | Enable Redis auth | `false` |

## Examples

### Production Configuration

```yaml
replicaCount: 5

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.production.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: api-tls
      hosts:
        - api.production.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20

externalSecrets:
  enabled: true
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
```

### Development Configuration

```yaml
replicaCount: 1

ingress:
  enabled: false

autoscaling:
  enabled: false

resources:
  limits:
    cpu: 250m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

postgresql:
  enabled: true
  primary:
    persistence:
      size: 1Gi

redis:
  enabled: true
```

## Testing

```bash
# Run helm lint
helm lint ./helm/my-api

# Render templates locally
helm template my-api ./helm/my-api

# Run helm tests after installation
helm test my-api -n my-api
```

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n my-api -l app.kubernetes.io/name=my-api
```

### View logs
```bash
kubectl logs -n my-api -l app.kubernetes.io/name=my-api -f
```

### Describe deployment
```bash
kubectl describe deployment -n my-api my-api
```
