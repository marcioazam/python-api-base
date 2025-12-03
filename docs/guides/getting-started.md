# Getting Started

## Overview

This guide will help you set up and run Python API Base locally.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/example/python-api-base.git
cd python-api-base
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync --dev

# Or using pip
pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required: SECURITY__SECRET_KEY (min 32 characters)
```

### 4. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Or use existing services and update .env
```

### 5. Run Migrations

```bash
# Apply database migrations
uv run alembic upgrade head
```

### 6. Start Application

```bash
# Development mode with auto-reload
uv run uvicorn src.main:app --reload

# Production mode
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Verify Installation

### Health Check

```bash
curl http://localhost:8000/health/live
# {"status": "ok"}

curl http://localhost:8000/health/ready
# {"status": "ok", "database": "ok", "redis": "ok"}
```

### API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
python-api-base/
├── src/                    # Source code
│   ├── core/              # Core layer (config, DI, protocols)
│   ├── domain/            # Domain layer (entities, specs)
│   ├── application/       # Application layer (use cases)
│   ├── infrastructure/    # Infrastructure layer (DB, cache)
│   ├── interface/         # Interface layer (API, middleware)
│   └── main.py            # Application entry point
├── tests/                  # Test files
├── docs/                   # Documentation
├── alembic/                # Database migrations
└── deployments/            # Deployment configs
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECURITY__SECRET_KEY` | Yes | - | JWT signing key (min 32 chars) |
| `DATABASE__URL` | Yes | - | PostgreSQL connection URL |
| `REDIS__URL` | No | `redis://localhost:6379` | Redis connection URL |
| `DEBUG` | No | `false` | Enable debug mode |

### Example .env

```bash
# Application
APP_NAME=My API
DEBUG=true
VERSION=1.0.0

# Database
DATABASE__URL=postgresql+asyncpg://user:pass@localhost/mydb
DATABASE__POOL_SIZE=10

# Security
SECURITY__SECRET_KEY=your-secret-key-at-least-32-characters
SECURITY__CORS_ORIGINS=["http://localhost:3000"]

# Redis
REDIS__URL=redis://localhost:6379

# Observability
OBSERVABILITY__LOG_LEVEL=DEBUG
OBSERVABILITY__LOG_FORMAT=text
```

## Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test type
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/properties/
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Follow the [Bounded Context Guide](bounded-context-guide.md) for new features.

### 3. Run Checks

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/

# Tests
uv run pytest
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

## Common Tasks

### Create New Entity

```bash
python scripts/generate_entity.py product --fields "name:str,price:float"
```

### Create Migration

```bash
uv run alembic revision --autogenerate -m "Add products table"
uv run alembic upgrade head
```

### Generate Config Docs

```bash
python scripts/generate_config_docs.py --output docs/configuration.md
```

## Troubleshooting

### Database Connection Failed

1. Check PostgreSQL is running: `docker ps`
2. Verify DATABASE__URL in .env
3. Check network connectivity

### Redis Connection Failed

1. Check Redis is running: `docker ps`
2. Verify REDIS__URL in .env
3. Try: `redis-cli ping`

### Import Errors

1. Ensure virtual environment is activated
2. Run: `uv sync --dev`
3. Check Python version: `python --version`

## Next Steps

- [Architecture Overview](../architecture.md)
- [API Documentation](../api/index.md)
- [Testing Guide](testing-guide.md)
- [Contributing](contributing.md)
