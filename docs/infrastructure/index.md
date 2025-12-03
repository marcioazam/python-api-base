# Infrastructure Guides

## Overview

Guias de integração com serviços de infraestrutura externos.

## Infrastructure Diagram

```mermaid
graph TB
    API[Python API Base]
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        ES[(Elasticsearch)]
    end
    
    subgraph "Messaging"
        KAFKA[Apache Kafka]
        RABBIT[RabbitMQ]
    end
    
    subgraph "Storage"
        MINIO[MinIO/S3]
    end
    
    API --> PG
    API --> REDIS
    API --> ES
    API --> KAFKA
    API --> RABBIT
    API --> MINIO
```

## Services

| Service | Purpose | Documentation |
|---------|---------|---------------|
| PostgreSQL | Primary database | [postgresql.md](postgresql.md) |
| Redis | Cache & sessions | [redis.md](redis.md) |
| Kafka | Event streaming | [kafka.md](kafka.md) |
| MinIO | Object storage | [minio.md](minio.md) |
| Elasticsearch | Search engine | [elasticsearch.md](elasticsearch.md) |

## Quick Start

```bash
# Start all services
docker compose -f deployments/docker/docker-compose.dev.yml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Environment Variables

```bash
# PostgreSQL
DATABASE__URL=postgresql+asyncpg://user:pass@localhost:5432/mydb

# Redis
REDIS__URL=redis://localhost:6379/0

# Kafka
KAFKA__BOOTSTRAP_SERVERS=localhost:9092

# MinIO
MINIO__ENDPOINT=localhost:9000
MINIO__ACCESS_KEY=minioadmin
MINIO__SECRET_KEY=minioadmin

# Elasticsearch
ELASTICSEARCH__URL=http://localhost:9200
```

## Health Checks

```bash
# PostgreSQL
pg_isready -h localhost -p 5432

# Redis
redis-cli ping

# Kafka
kafka-topics.sh --bootstrap-server localhost:9092 --list

# MinIO
curl http://localhost:9000/minio/health/live

# Elasticsearch
curl http://localhost:9200/_cluster/health
```
