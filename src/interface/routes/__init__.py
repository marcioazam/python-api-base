"""API routes module.

**Feature: interface-middleware-routes-analysis**
**Validates: Requirements 2.1**

This module provides shared route components and utilities.
The actual API routers are organized in versioned directories:

- `interface.v1.*` - API v1 routes (current stable)
- `interface.v2.*` - API v2 routes (enhanced features)

Structure:
    routes/
    ├── __init__.py      - This file, exports shared components
    ├── auth/            - Authentication service components
    │   ├── constants.py - Demo users (dev only)
    │   └── service.py   - JWT and token store services
    └── README.md        - Documentation

Usage:
    from interface.routes.auth import get_jwt_service, get_token_store
    from interface.routes.auth import DEMO_USERS  # Dev only!
"""

# Authentication service components
from interface.routes.auth import (
    DEMO_USERS,
    MessageResponse,
    RefreshRequest,
    RevokeAllResponse,
    RevokeTokenRequest,
    TokenResponse,
    UserResponse,
    get_jwt_service,
    get_token_store,
    set_token_store,
)

__all__ = [
    # Auth service
    "DEMO_USERS",
    "MessageResponse",
    "RefreshRequest",
    "RevokeAllResponse",
    "RevokeTokenRequest",
    "TokenResponse",
    "UserResponse",
    "get_jwt_service",
    "get_token_store",
    "set_token_store",
]
