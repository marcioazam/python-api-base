# Deployment

## Overview

Deployment documentation for Python API Base.

## Docker

### Dockerfile

```dockerfile
FROM python:3.12-slim as builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE__URL=postgresql+asyncpg://user:pass@postgres/db
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: pass
  
  redis:
    image: redis:7
```

## Kubernetes

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-api-base
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: python-api-base:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
```

## Health Checks

| Probe | Path | Purpose |
|-------|------|---------|
| Liveness | `/health/live` | Is app running? |
| Readiness | `/health/ready` | Can app serve traffic? |

## Environment Configuration

| Environment | Replicas | Resources |
|-------------|----------|-----------|
| Development | 1 | 256Mi/250m |
| Staging | 2 | 512Mi/500m |
| Production | 3+ | 1Gi/1000m |

## Related

- [Docker](#docker)
- [Kubernetes](#kubernetes)
- [Monitoring](monitoring.md)
