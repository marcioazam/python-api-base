# Docker Deployment

Complete Docker setup for Python API Base with development, production, and infrastructure configurations.

## Quick Start

```bash
# Development (hot reload)
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up

# Production
docker compose -f docker-compose.base.yml -f docker-compose.production.yml up -d

# With full infrastructure (Kafka, RabbitMQ, etc.)
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up -d
```

## Directory Structure

```
deployments/docker/
├── configs/
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       └── datasources/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts/
│   └── nginx/
├── dockerfiles/
│   ├── api.Dockerfile          # Production
│   ├── api.dev.Dockerfile      # Development
│   └── worker.Dockerfile       # Background worker
├── scripts/
│   └── init-db.sql
├── docker-compose.base.yml     # Core services (API, Postgres, Redis)
├── docker-compose.dev.yml      # Development overrides
├── docker-compose.production.yml # Production settings
└── docker-compose.infra.yml    # Infrastructure (Kafka, RabbitMQ, etc.)
```

## Compose Files

| File | Purpose | Use Case |
|------|---------|----------|
| `base.yml` | Core services | Always required |
| `dev.yml` | Hot reload, debug | Local development |
| `production.yml` | Security, limits | Production deploy |
| `infra.yml` | Messaging, storage | Full stack |

## Services

### Core (base.yml)

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Cache & rate limiting |

### Infrastructure (infra.yml)

| Service | Port(s) | Description |
|---------|---------|-------------|
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3000 | Visualization |
| `elasticsearch` | 9200 | Log storage |
| `kibana` | 5601 | Log UI |
| `kafka` | 9092, 29092 | Event streaming |
| `rabbitmq` | 5672, 15672 | Task queue |
| `minio` | 9000, 9001 | S3 storage |
| `scylladb` | 9042 | NoSQL database |
| `keycloak` | 8080 | Identity management |

## Usage Examples

### Development

```bash
# Start with hot reload
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up

# View logs
docker compose logs -f api

# Rebuild after dependency changes
docker compose build --no-cache api
```

### Production

```bash
# Create .env file with secrets
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
SECURITY_SECRET_KEY=your-super-secret-key-min-32-chars
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_secure_password
EOF

# Deploy
docker compose -f docker-compose.base.yml -f docker-compose.production.yml up -d

# Scale API
docker compose up -d --scale api=3
```

### Full Stack

```bash
# All services including infrastructure
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.infra.yml \
  up -d

# Check service health
docker compose ps
```

## Environment Variables

### Required (Production)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECURITY_SECRET_KEY` | JWT signing key (min 32 chars) |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | 8000 | API exposed port |
| `LOG_LEVEL` | INFO | Log verbosity |
| `ENVIRONMENT` | development | Environment name |
| `GRAFANA_USER` | admin | Grafana admin user |
| `GRAFANA_PASSWORD` | admin | Grafana admin password |

## Building Images

```bash
# Production API
docker build -f dockerfiles/api.Dockerfile -t python-api:latest ../..

# Development API
docker build -f dockerfiles/api.dev.Dockerfile -t python-api:dev ../..

# Worker
docker build -f dockerfiles/worker.Dockerfile -t python-api-worker:latest ../..
```

## Health Checks

All services have health checks configured:

```bash
# Check all services
docker compose ps

# API health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health
```

## Monitoring

### Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Kibana | http://localhost:5601 | - |
| RabbitMQ | http://localhost:15672 | guest/guest |
| Keycloak | http://localhost:8080 | admin/admin |
| MinIO | http://localhost:9001 | minioadmin/minioadmin |

### Metrics Endpoint

The API exposes Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs api

# Check health
docker inspect --format='{{.State.Health.Status}}' python-api
```

### Database connection issues

```bash
# Verify postgres is healthy
docker compose exec postgres pg_isready -U postgres

# Check network
docker network inspect python-api-network
```

### Clean restart

```bash
# Stop and remove everything
docker compose down -v

# Remove all images
docker compose down --rmi all
```
