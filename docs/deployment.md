# Deployment Guide

## Visão Geral

Este guia cobre as diferentes opções de deployment do Python API Base.

## Opções de Deployment

| Opção | Complexidade | Escalabilidade | Custo |
|-------|--------------|----------------|-------|
| Docker Compose | Baixa | Baixa | Baixo |
| Kubernetes | Alta | Alta | Médio-Alto |
| Serverless (AWS Lambda) | Média | Alta | Variável |
| Vercel | Baixa | Média | Baixo-Médio |

---

## Docker Compose

### Produção

```bash
cd deployments/docker
docker compose -f docker-compose.production.yml up -d
```

### Estrutura

```
deployments/docker/
├── docker-compose.base.yml      # Configuração base
├── docker-compose.dev.yml       # Desenvolvimento
├── docker-compose.infra.yml     # Infraestrutura
├── docker-compose.production.yml # Produção
├── dockerfiles/
│   ├── Dockerfile.api           # API principal
│   └── Dockerfile.worker        # Workers
├── configs/
│   ├── nginx.conf               # Nginx config
│   └── prometheus.yml           # Prometheus config
└── scripts/
    ├── entrypoint.sh            # Entrypoint
    └── healthcheck.sh           # Health check
```

### Dockerfile

```dockerfile
# deployments/docker/dockerfiles/Dockerfile.api
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.production.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: ../..
      dockerfile: deployments/docker/dockerfiles/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE__URL=postgresql+asyncpg://user:pass@db:5432/mydb
      - REDIS__URL=redis://redis:6379/0
      - SECURITY__SECRET_KEY=${SECURITY__SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./configs/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

---

## Kubernetes

### Estrutura

```
deployments/k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
├── api/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   └── ingress.yaml
├── worker/
│   ├── deployment.yaml
│   └── service.yaml
├── monitoring/
│   ├── prometheus.yaml
│   └── grafana.yaml
└── jobs/
    └── migration.yaml
```

### Deployment

```yaml
# deployments/k8s/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: python-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: ghcr.io/example/python-api-base:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE__URL
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: database-url
            - name: SECURITY__SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: secret-key
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          startupProbe:
            httpGet:
              path: /health/startup
              port: 8000
            failureThreshold: 30
            periodSeconds: 10
```

### Service

```yaml
# deployments/k8s/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: python-api
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### HPA (Horizontal Pod Autoscaler)

```yaml
# deployments/k8s/api/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: python-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Ingress

```yaml
# deployments/k8s/api/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: python-api
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
```

### Deploy Commands

```bash
# Aplicar configurações
kubectl apply -f deployments/k8s/base/
kubectl apply -f deployments/k8s/api/

# Verificar status
kubectl get pods -n python-api
kubectl get services -n python-api

# Ver logs
kubectl logs -f deployment/api -n python-api

# Escalar manualmente
kubectl scale deployment api --replicas=5 -n python-api
```

---

## Helm Chart

### Estrutura

```
deployments/helm/api/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── _helpers.tpl
└── charts/
```

### values.yaml

```yaml
# deployments/helm/api/values.yaml
replicaCount: 3

image:
  repository: ghcr.io/example/python-api-base
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: api-tls
      hosts:
        - api.example.com

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  DATABASE__URL: ""
  REDIS__URL: ""
  SECURITY__SECRET_KEY: ""
```

### Deploy Commands

```bash
# Instalar
helm install api deployments/helm/api/ -f values-production.yaml

# Atualizar
helm upgrade api deployments/helm/api/ -f values-production.yaml

# Rollback
helm rollback api 1

# Desinstalar
helm uninstall api
```

---

## Terraform

### Estrutura

```
deployments/terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
├── versions.tf
├── aws.tf
├── azure.tf
├── gcp.tf
├── modules/
│   ├── vpc/
│   ├── rds/
│   ├── elasticache/
│   └── ecs/
└── environments/
    ├── dev/
    ├── staging/
    └── production/
```

### AWS ECS

```hcl
# deployments/terraform/aws.tf
module "ecs_cluster" {
  source = "./modules/ecs"

  cluster_name = "python-api-cluster"
  
  services = {
    api = {
      image         = "ghcr.io/example/python-api-base:latest"
      cpu           = 256
      memory        = 512
      desired_count = 3
      port          = 8000
      
      environment = {
        DATABASE__URL = var.database_url
        REDIS__URL    = var.redis_url
      }
      
      secrets = {
        SECURITY__SECRET_KEY = aws_secretsmanager_secret.api_secret.arn
      }
    }
  }
}

module "rds" {
  source = "./modules/rds"

  identifier     = "python-api-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.medium"
  
  allocated_storage = 20
  storage_encrypted = true
  
  database_name = "mydb"
  username      = "admin"
}

module "elasticache" {
  source = "./modules/elasticache"

  cluster_id      = "python-api-redis"
  engine          = "redis"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
}
```

### Deploy Commands

```bash
# Inicializar
terraform init

# Planejar
terraform plan -var-file=environments/production/terraform.tfvars

# Aplicar
terraform apply -var-file=environments/production/terraform.tfvars

# Destruir
terraform destroy -var-file=environments/production/terraform.tfvars
```

---

## Serverless (AWS Lambda)

### Estrutura

```
deployments/serverless/aws-lambda/
├── handler.py
├── serverless.yml
└── requirements.txt
```

### handler.py

```python
from mangum import Mangum
from src.main import app

handler = Mangum(app, lifespan="off")
```

### serverless.yml

```yaml
service: python-api-base

provider:
  name: aws
  runtime: python3.12
  region: us-east-1
  memorySize: 512
  timeout: 30
  environment:
    DATABASE__URL: ${ssm:/python-api/database-url}
    SECURITY__SECRET_KEY: ${ssm:/python-api/secret-key}

functions:
  api:
    handler: handler.handler
    events:
      - httpApi:
          path: /{proxy+}
          method: ANY
      - httpApi:
          path: /
          method: ANY

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    slim: true
```

---

## CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: uv run pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: deployments/docker/dockerfiles/Dockerfile.api
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - run: |
          kubectl set image deployment/api \
            api=ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## Checklist de Produção

### Segurança

- [ ] Secret key forte (32+ caracteres)
- [ ] CORS configurado corretamente
- [ ] Rate limiting habilitado
- [ ] Headers de segurança configurados
- [ ] TLS/HTTPS habilitado
- [ ] Secrets em vault/secrets manager

### Performance

- [ ] Connection pooling configurado
- [ ] Cache habilitado (Redis)
- [ ] Compressão habilitada
- [ ] CDN para assets estáticos

### Observabilidade

- [ ] Logging estruturado (JSON)
- [ ] Tracing distribuído
- [ ] Métricas Prometheus
- [ ] Alertas configurados
- [ ] Dashboards criados

### Resiliência

- [ ] Health checks configurados
- [ ] Circuit breakers habilitados
- [ ] Retry policies configuradas
- [ ] Graceful shutdown
- [ ] Backup de banco de dados

### Escalabilidade

- [ ] Horizontal Pod Autoscaler
- [ ] Load balancer configurado
- [ ] Database read replicas
- [ ] Cache distribuído
