# ADR-015: Middleware Stack Order and Configuration

## Status

Accepted

## Context

The application requires multiple middleware components for:
- Request tracing and correlation
- Logging and observability
- Security (CORS, headers, rate limiting)
- Resilience (circuit breaker)
- Multi-tenancy
- Audit trail

The order of middleware execution is critical for correct behavior:
- Request ID must be generated first for correlation
- Logging must capture all requests
- Security headers must be added to all responses
- Rate limiting should happen before expensive operations

## Decision

We establish the following middleware stack order (outermost to innermost):

1. **RequestIDMiddleware** - Generate/propagate X-Request-ID
2. **LoggingMiddleware** - Correlation ID and structured logging
3. **RequestLoggerMiddleware** - Detailed request/response logging
4. **CORSMiddleware** - Cross-origin resource sharing
5. **SecurityHeadersMiddleware** - Security headers (CSP, HSTS, etc.)
6. **RequestSizeLimitMiddleware** - Limit request body size
7. **ResilienceMiddleware** - Circuit breaker pattern
8. **MultitenancyMiddleware** - Tenant context resolution
9. **AuditMiddleware** - Request audit trail
10. **RateLimitMiddleware** - Rate limiting

### Configuration Decisions

#### Request Size Limits
- Default: 10MB
- Upload routes: 50MB
- Import routes: 20MB

#### Rate Limits
- Default: 100 requests/minute
- GET operations: 100/min
- POST/PUT operations: 20/min
- DELETE operations: 10/min

#### Security Headers
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- HSTS: max-age=31536000; includeSubDomains; preload
- CSP: Configured for Swagger UI compatibility

## Consequences

### Positive

- Clear, documented middleware order
- Request correlation across all logs
- Consistent security headers on all responses
- Protection against large request attacks
- Circuit breaker prevents cascade failures
- Audit trail for compliance

### Negative

- Middleware stack adds latency (~1-5ms per request)
- Memory overhead for audit records
- Complexity in debugging middleware interactions

### Neutral

- TimeoutMiddleware not integrated (generic implementation)
- FeatureFlagMiddleware requires external configuration
- Some middlewares excluded from health/metrics paths

## Alternatives Considered

### 1. Single Combined Middleware
- Rejected: Violates single responsibility principle
- Harder to test and maintain

### 2. Conditional Middleware Loading
- Partially adopted: Some middlewares are optional
- Full conditional loading adds complexity

### 3. Middleware Chain Pattern
- Available but not used for FastAPI
- Better suited for custom request processing

## References

- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)

## Feature Reference

**Feature: interface-middleware-routes-analysis**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
