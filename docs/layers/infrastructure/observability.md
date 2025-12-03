# Observability Infrastructure

## Overview

Observability infrastructure provides comprehensive monitoring through traces, metrics, and structured logs using OpenTelemetry and structlog.

## Location

```
src/infrastructure/observability/
├── __init__.py
├── anomaly.py              # Anomaly detection
├── correlation_id.py       # Request correlation
├── logging_config.py       # Logging setup
├── logging_middleware.py   # Log middleware
├── metrics.py              # Custom metrics
├── middleware.py           # Observability middleware
├── tracing.py              # Tracing utilities
└── telemetry/              # OpenTelemetry setup
```

## Tracing (OpenTelemetry)

### Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_tracing(service_name: str, otlp_endpoint: str) -> None:
    """Configure OpenTelemetry tracing."""
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": service_name,
        })
    )
    
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
```

### Tracing Decorator

```python
from functools import wraps
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def traced(
    name: str | None = None,
    attributes: dict | None = None,
):
    """Decorator for tracing functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator
```

### Usage

```python
@traced(name="process_order", attributes={"service": "orders"})
async def process_order(order_id: str) -> Order:
    # Span created automatically
    # Exceptions recorded as events
    return await order_service.process(order_id)
```

## Logging (structlog)

### Configuration

```python
import structlog

def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
) -> None:
    """Configure structured logging."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Usage

```python
import structlog

logger = structlog.get_logger()

# Simple logging
logger.info("User created", user_id="123", email="user@example.com")

# With context
logger.bind(request_id="abc-123").info("Processing request")

# Error logging
logger.error(
    "Database error",
    error=str(e),
    query="SELECT * FROM users",
    exc_info=True,
)
```

### Log Output (JSON)

```json
{
  "event": "User created",
  "user_id": "123",
  "email": "user@example.com",
  "level": "info",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "correlation_id": "abc-123"
}
```

## Metrics (Prometheus)

### Custom Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Request counter
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Request duration
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Active connections
active_connections = Gauge(
    "active_connections",
    "Number of active connections",
)
```

### Metrics Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method
        endpoint = request.url.path
        
        with http_request_duration.labels(
            method=method,
            endpoint=endpoint,
        ).time():
            response = await call_next(request)
        
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()
        
        return response
```

### Metrics Endpoint

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@router.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

## Correlation ID

### Middleware

```python
from uuid import uuid4
import structlog

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid4()),
        )
        
        # Add to structlog context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
        )
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
```

## Dashboard Queries

### Grafana - Request Rate

```promql
rate(http_requests_total[5m])
```

### Grafana - Error Rate

```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ sum(rate(http_requests_total[5m])) * 100
```

### Grafana - P99 Latency

```promql
histogram_quantile(0.99, 
  rate(http_request_duration_seconds_bucket[5m])
)
```

## Configuration

```python
class ObservabilitySettings(BaseSettings):
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    otlp_endpoint: str | None = None
    service_name: str = "python-api-base"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    tracing_sample_rate: float = 1.0
```

## Related Documentation

- [Monitoring](../../operations/monitoring.md)
- [Core Layer](../core/index.md)
- [Resilience](resilience.md)
