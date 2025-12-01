# API Security

## Authentication

- JWT Bearer tokens for API authentication
- OAuth2 password flow for token acquisition
- Refresh tokens for session extension

## Authorization

- Role-Based Access Control (RBAC)
- Permission-based endpoint protection
- Admin-only endpoints require `admin` role

## Security Headers

- CORS configured for allowed origins
- CSP headers for XSS protection
- HSTS for HTTPS enforcement

## Rate Limiting

- Redis-based sliding window rate limiting
- Per-user and per-IP limits
- Configurable limits per endpoint
