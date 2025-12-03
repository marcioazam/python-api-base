# API Documentation

## Overview

Python API Base exposes multiple API interfaces for different use cases.

## API Types

| Type | Description | Documentation |
|------|-------------|---------------|
| REST API | HTTP/JSON endpoints following RESTful principles | [REST API](rest/index.md) |
| GraphQL | Query language for flexible data fetching | [GraphQL](graphql/index.md) |
| WebSocket | Real-time bidirectional communication | [WebSocket](websocket/index.md) |
| Internal | Service-to-service communication contracts | [Internal APIs](internal/index.md) |

## API Versioning

The API uses URL-based versioning:
- `/api/v1/*` - Version 1 (current stable)
- `/api/v2/*` - Version 2 (experimental)

See [Versioning Strategy](versioning.md) for details.

## Authentication

All protected endpoints require JWT authentication:
- Access Token: Short-lived (30 minutes default)
- Refresh Token: Long-lived (7 days default)

See [Security](security.md) for authentication details.

## Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |
| `/openapi.json` | GET | OpenAPI specification |

## Quick Navigation

- [Back to Index](../index.md)
- [Security](security.md)
- [Versioning](versioning.md)
