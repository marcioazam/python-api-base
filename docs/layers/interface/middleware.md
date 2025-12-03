# Middleware Stack

## Overview

O middleware stack processa requisições em ordem, aplicando logging, segurança, rate limiting e auditoria.

## Middleware Order

```python
def setup_middleware(app: FastAPI) -> None:
    # 1. Logging (outermost - first in, last out)
    app.add_middleware(LoggingMiddleware)
    
    # 2. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 3. Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Rate Limiting
    app.add_middleware(RateLimitMiddleware, limit=settings.security.rate_limit)
    
    # 5. Authentication
    app.add_middleware(AuthMiddleware)
    
    # 6. Audit (innermost - last in, first out)
    app.add_middleware(AuditMiddleware)
```

## Logging Middleware

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        
        # Bind to context
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        start_time = time.perf_counter()
        
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )
        
        response = await call_next(request)
        
        duration = time.perf_counter() - start_time
        
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration * 1000,
        )
        
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

## Security Headers Middleware

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
```

## Rate Limit Middleware

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: str = "100/minute"):
        super().__init__(app)
        self._limit, self._window = self._parse_limit(limit)
        self._cache: dict[str, list[float]] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host
        key = f"{client_ip}:{request.url.path}"
        
        now = time.time()
        window_start = now - self._window
        
        # Clean old entries
        self._cache[key] = [t for t in self._cache.get(key, []) if t > window_start]
        
        if len(self._cache[key]) >= self._limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(self._window)},
            )
        
        self._cache[key].append(now)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(self._limit - len(self._cache[key]))
        
        return response
```

## Auth Middleware

```python
class AuthMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json", "/auth/login"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing token"})
        
        token = auth_header.split(" ")[1]
        
        try:
            payload = jwt_service.verify(token)
            request.state.user = payload
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        
        return await call_next(request)
```

## Audit Middleware

```python
class AuditMiddleware(BaseHTTPMiddleware):
    AUDITED_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in self.AUDITED_METHODS:
            return await call_next(request)
        
        user_id = getattr(request.state, "user", {}).get("user_id")
        
        response = await call_next(request)
        
        if response.status_code < 400:
            await audit_store.log(AuditRecord(
                action=request.method,
                resource=request.url.path,
                user_id=user_id,
                status_code=response.status_code,
                timestamp=datetime.utcnow(),
            ))
        
        return response
```

## Best Practices

1. **Order matters** - Logging first, audit last
2. **Keep middleware thin** - Delegate to services
3. **Handle errors gracefully** - Don't break the chain
4. **Use context vars** - For request-scoped data
5. **Exclude health checks** - From auth and rate limiting
