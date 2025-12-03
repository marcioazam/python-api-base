# Interface Routes

## Overview

This directory contains shared route components and utilities for the API.
The actual API routers are organized in versioned directories under `interface/`.

## Directory Structure

```
interface/
├── routes/              # Shared components (this directory)
│   ├── __init__.py      # Exports shared components
│   ├── auth/            # Authentication service components
│   │   ├── constants.py # Demo users (development only)
│   │   └── service.py   # JWT and token store services
│   └── README.md        # This file
├── v1/                  # API v1 routes (current stable)
│   ├── auth/            # Authentication endpoints
│   ├── examples/        # ItemExample and PedidoExample endpoints
│   ├── health_router.py # Health check endpoints
│   └── users_router.py  # User management endpoints
├── v2/                  # API v2 routes (enhanced features)
│   └── examples_router.py # Enhanced examples with versioning
└── middleware/          # Request processing middleware
```

## Usage

### Authentication Services

```python
from interface.routes.auth import get_jwt_service, get_token_store

# Get JWT service for token operations
jwt_service = get_jwt_service()
token = jwt_service.create_access_token(user_id="user-123", roles=["admin"])

# Get token store for refresh token management
token_store = get_token_store()
await token_store.store(refresh_token, user_id="user-123")
```

### Demo Users (Development Only)

```python
from interface.routes.auth import DEMO_USERS

# WARNING: Only for development/testing!
# Do NOT use in production environments.
user = DEMO_USERS.get("admin")  # {"password": "admin123", "roles": ["admin"]}
```

## API Versioning

| Version | Prefix | Status | Description |
|---------|--------|--------|-------------|
| v1 | `/api/v1` | Stable | Current production API |
| v2 | `/api/v2` | Active | Enhanced features with deprecation headers |

## Related Documentation

- [API Architecture](../../../docs/architecture.md)
- [Authentication Guide](../../../docs/authentication.md)
- [Middleware Stack](../middleware/README.md)

## Feature References

**Feature: interface-middleware-routes-analysis**
**Validates: Requirements 2.1, 2.2**
