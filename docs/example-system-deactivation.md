# Example System Deactivation Guide

This document describes how to deactivate the ItemExample and PedidoExample demonstration system when transitioning to production or developing your real application.

## ⚠️ Important: Core vs Example System

**DO NOT REMOVE:**

- ✅ **Users & RBAC** (`/api/v1/auth/*`, `/api/v1/users/*`) - **PERMANENT CORE API**
- ✅ **Health Check** (`/health/*`) - **PERMANENT CORE API**
- ✅ Database tables: `users`, `roles`, `user_roles`

**SAFE TO REMOVE:**

- ❌ **Examples** (`/api/v1/examples/*`) - ItemExample, PedidoExample
- ❌ Database tables: `items`, `pedidos`, `pedido_items`

## Overview

The Example System demonstrates all Python API Base 2025 features:
- **Domain Layer**: Entities, Value Objects, Specifications, Domain Events
- **Application Layer**: DTOs, Mappers, Use Cases, CQRS
- **Infrastructure Layer**: Repositories, Models, Database
- **Interface Layer**: REST API, Middleware integration

## Quick Deactivation (3 Steps)

### Step 1: Remove Router Registration

Edit `src/main.py` or your router configuration:

```python
# REMOVE these lines:
from interface.v1.examples import examples_router
app.include_router(examples_router, prefix="/api/v1")
```

### Step 2: Remove Migration

```bash
# Downgrade migration
alembic downgrade -1

# Or remove migration file
rm alembic/versions/20241201_000000_example_system.py
```

### Step 3: Remove Source Files

```bash
# PowerShell
Remove-Item -Recurse -Force src/domain/examples
Remove-Item -Recurse -Force src/application/examples
Remove-Item -Recurse -Force src/interface/v1/examples
Remove-Item -Force src/infrastructure/db/models/examples.py
Remove-Item -Force src/infrastructure/db/repositories/examples.py
Remove-Item -Force scripts/seed_examples.py

# Bash/Linux
rm -rf src/domain/examples
rm -rf src/application/examples
rm -rf src/interface/v1/examples
rm -f src/infrastructure/db/models/examples.py
rm -f src/infrastructure/db/repositories/examples.py
rm -f scripts/seed_examples.py
```

## Complete File List

All files related to the Example System:

```
# Domain Layer
src/domain/examples/
├── __init__.py
├── item_example.py          # ItemExample entity, Money VO, events
├── pedido_example.py         # PedidoExample aggregate, events
└── specifications.py         # Business rule specifications

# Application Layer
src/application/examples/
├── __init__.py
├── dtos.py                   # Request/Response DTOs
├── mappers.py                # Entity to DTO mappers
└── use_cases.py              # Business logic orchestration

# Infrastructure Layer
src/infrastructure/db/models/examples.py      # SQLModel database models
src/infrastructure/db/repositories/examples.py # Repository implementations

# Interface Layer
src/interface/v1/examples/
├── __init__.py
└── router.py                 # FastAPI routes

# Database
alembic/versions/20241201_000000_example_system.py  # Migration

# Docker
deployments/docker/docker-compose.example.yml  # Demo environment
deployments/docker/init-db.sql                  # DB initialization

# Scripts
scripts/seed_examples.py      # Demo data seeder

# Documentation
docs/example-system-deactivation.md  # This file
```

## Keeping Parts of the Example

If you want to use parts of the example as templates:

### Keep Only Domain Patterns

```bash
# Keep domain as reference, remove rest
rm -rf src/application/examples
rm -rf src/interface/v1/examples
rm -f src/infrastructure/db/models/examples.py
rm -f src/infrastructure/db/repositories/examples.py
```

### Copy Pattern for New Entity

```bash
# Copy ItemExample as template for your entity
cp -r src/domain/examples src/domain/your_entity
# Then rename classes and adjust as needed
```

## Database Cleanup

If the example was deployed to a database:

```sql
-- Drop tables (in order due to foreign keys)
DROP TABLE IF EXISTS pedido_item_examples CASCADE;
DROP TABLE IF EXISTS pedido_examples CASCADE;
DROP TABLE IF EXISTS item_examples CASCADE;

-- Remove from alembic version
DELETE FROM alembic_version WHERE version_num = 'example_system_001';
```

## Environment Variables

Remove example-related environment variables:

```bash
# Remove from .env
# ENABLE_EXAMPLES=true  # Delete this line
```

## Docker Cleanup

```bash
# Stop example containers
docker-compose -f deployments/docker/docker-compose.example.yml down -v

# Remove images
docker rmi python-api-example

# Remove volumes
docker volume rm python-api-base_postgres_data
docker volume rm python-api-base_redis_data
```

## Verification Checklist

After deactivation, verify:

- [ ] API starts without errors
- [ ] `/api/v1/examples/*` endpoints return 404
- [ ] No import errors in logs
- [ ] Database has no example tables
- [ ] Tests pass (remove example tests too)

## Creating Your Real Application

Use the example as a template:

1. **Copy structure**: Use the same layer organization
2. **Rename entities**: Replace `ItemExample` with your domain entities
3. **Keep patterns**: Maintain the same patterns (Result, Specification, etc.)
4. **Update DTOs**: Create your own request/response models
5. **Write tests**: Follow the same testing patterns

### Example Transformation

```python
# FROM (Example)
class ItemExample(AuditableEntity[str]):
    name: str
    price: Money

# TO (Your Domain)
class Product(AuditableEntity[str]):
    title: str
    pricing: PricingInfo
```

## API Interfaces

### Current: REST API (FastAPI)

The Python API Base uses **FastAPI** for REST endpoints:

```http
GET    /api/v1/auth/me
POST   /api/v1/auth/login
POST   /api/v1/auth/register
GET    /api/v1/users
GET    /api/v1/users/{user_id}
POST   /api/v1/users/{user_id}/roles
DELETE /api/v1/users/{user_id}/roles/{role_name}
```

### GraphQL Support

**Current Status:** ❌ **NOT IMPLEMENTED**

GraphQL is **not included** in the base architecture. To add GraphQL:

1. **Install dependency:**

   ```bash
   pip install strawberry-graphql strawberry-graphql-fastapi
   ```

2. **Create GraphQL schema** in `src/interface/graphql/schema.py`

3. **Register GraphQL router** in `src/main.py`

4. **Recommended approach:**
   - Keep REST API for core operations
   - Add GraphQL as optional interface
   - Use same domain models for both

### Alternative Interfaces

To add other interfaces:

- **gRPC**: Use `grpcio` + Protocol Buffers
- **WebSocket**: FastAPI native support
- **GraphQL**: Strawberry or Graphene
- **SOAP**: Not recommended (use REST instead)

## Support

For questions about the architecture patterns demonstrated:

- See `/docs/architecture/` for layer documentation
- See `/docs/adr/` for architectural decisions
- See `/tests/properties/` for behavior specifications

---

**Feature:** example-system-demo  
**Created:** 2024-12-01  
**Updated:** 2024-12-01 - Added Core vs Example distinction, GraphQL status  
**Purpose:** Development reference and testing demonstration
