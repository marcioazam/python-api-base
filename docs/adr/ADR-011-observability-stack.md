# ADR-011: Observability Stack

## Status
Accepted

## Context

The system needs comprehensive observability that:
- Provides distributed tracing across services
- Enables structured logging for analysis
- Exposes metrics for monitoring and alerting
- Supports correlation across all three pillars

## Decision

We implement a three-pillar observability stack:

### Tracing (OpenTelemetry)

```python
# src/infrastructure/observability/tracing.py
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@traced(name="process_order", attributes={"service": "orders"})
async def process_order(order_id: str) -> Order:
    with tracer.start_as_current_span("validate_order") as span:
        span.set_attribute("order_id", order_id)
        # ... processing
```

**Configuration:**
```python
# src/core/config/observability.py
class ObservabilitySettings(BaseSettings):
    otlp_endpoint: str | None = None
    service_name: str = "python-api-base"
    trace_sample_rate: float = 1.0
```

### Logging (structlog)

```python
# src/infrastructure/observability/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()
logger.info(
    "user_created",
    user_id=user.id,
    email=user.email,
    trace_id=get_trace_id(),
)
```

**Log Format (JSON):**
```json
{
    "event": "user_created",
    "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "email": "user@example.com",
    "timestamp": "2024-12-02T10:30:00Z",
    "level": "info",
    "trace_id": "abc123",
    "span_id": "def456",
    "service": "python-api-base"
}
```

### Metrics (Prometheus)

```python
# src/infrastructure/prometheus/metrics.py
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
)
```

### Correlation

All three pillars share:
- `trace_id`: Distributed trace identifier
- `span_id`: Current span identifier
- `correlation_id`: Request correlation ID

```python
# src/infrastructure/observability/correlation_id.py
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id")

class CorrelationMiddleware:
    async def __call__(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID", str(uuid4()))
        correlation_id.set(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
```

## Consequences

### Positive
- Full visibility into system behavior
- Correlated logs, traces, and metrics
- Standard tooling (Grafana, Jaeger)
- Easy debugging of distributed issues

### Negative
- Additional infrastructure (collectors, storage)
- Performance overhead (minimal)
- Learning curve for team

### Neutral
- Requires Grafana/Jaeger setup
- Log volume management needed

## Alternatives Considered

1. **Logging only** - Rejected as insufficient for distributed systems
2. **Commercial APM (Datadog)** - Rejected for cost; can be added later
3. **Custom solution** - Rejected in favor of standards

## References

- [src/infrastructure/observability/](../../src/infrastructure/observability/)
- [src/infrastructure/prometheus/](../../src/infrastructure/prometheus/)
- [src/core/config/observability.py](../../src/core/config/observability.py)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
