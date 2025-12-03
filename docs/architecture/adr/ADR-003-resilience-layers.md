# ADR-003: Resilience Layers Strategy

**Status:** Accepted

**Date:** 2025-01-02

**Deciders:** Architecture Team

**Technical Story:** The system has two separate resilience implementations at different layers, which requires clarification of responsibilities and integration strategy.

---

## Context

The system currently has two distinct resilience pattern implementations:

### 1. Application Layer Resilience
Located in `src/application/common/middleware/`:

```python
# RetryMiddleware - For CommandBus
class RetryMiddleware:
    """Retry with exponential backoff for commands."""
    async def __call__(self, command: Any, next_handler: Callable) -> Any:
        for attempt in range(self._config.max_retries + 1):
            try:
                return await next_handler(command)
            except Exception as e:
                if not self._is_retryable(e):
                    raise
                await asyncio.sleep(self._calculate_delay(attempt))

# CircuitBreakerMiddleware - For CommandBus
class CircuitBreakerMiddleware:
    """Circuit breaker to prevent cascade failures in commands."""
    # CLOSED → OPEN → HALF_OPEN → CLOSED states

# ResilienceMiddleware - Combines both
class ResilienceMiddleware:
    """Combined retry + circuit breaker for CommandBus."""
```

**Status:** ⚠️ Created but NOT integrated to CommandBus

### 2. Infrastructure Layer Resilience
Located in `src/infrastructure/resilience/` and used in `src/interface/middleware/production.py`:

```python
# CircuitBreaker - For HTTP requests
class CircuitBreaker:
    """Infrastructure circuit breaker for external dependencies."""

# ResilienceMiddleware - HTTP middleware
class ResilienceMiddleware(BaseHTTPMiddleware):
    """Applied to HTTP requests via FastAPI middleware stack."""
    # ✅ ACTIVE in main.py:226-242
```

**Status:** ✅ Integrated and active

## Problem

This dual implementation creates confusion:
- Which layer should handle which failures?
- When to use application vs infrastructure resilience?
- Are they redundant or complementary?
- Should both be active simultaneously?

## Decision

**We adopt a layered resilience strategy with clear separation of concerns:**

### Layer 1: HTTP/Infrastructure Resilience (ACTIVE)
**Location:** `src/infrastructure/resilience/` + `src/interface/middleware/production.py`

**Responsibility:** Protect against external service and infrastructure failures

**Handles:**
- Database connection failures
- External API timeouts
- Network errors
- Infrastructure outages
- Rate limiting from downstream services

**Applied at:** HTTP request level (FastAPI middleware)

**Configuration:**
```python
# main.py
ResilienceMiddleware(
    failure_threshold=5,      # 5 failures → circuit opens
    timeout_seconds=30.0,     # 30s timeout per request
    enabled=True
)
```

**Status:** ✅ ACTIVE

### Layer 2: CQRS/Application Resilience (AVAILABLE)
**Location:** `src/application/common/middleware/`

**Responsibility:** Protect against specific command/query execution failures

**Handles:**
- Domain-specific transient errors
- Command-specific retry logic
- Fine-grained circuit breaking per command type
- Business operation failures

**Applied at:** CommandBus/QueryBus level

**Configuration:**
```python
# Future use when needed
command_bus.add_middleware(ResilienceMiddleware(
    retry_config=RetryConfig(max_retries=3),
    circuit_config=CircuitBreakerConfig(failure_threshold=5)
))
```

**Status:** ⚠️ AVAILABLE but not activated (reserved for future use)

## Rationale

### Why Two Layers?

1. **Different Failure Scopes:**
   - HTTP layer: Infrastructure, network, external services
   - CQRS layer: Domain operations, business logic

2. **Different Recovery Strategies:**
   - HTTP: Fast-fail, prevent cascades, protect all endpoints
   - CQRS: Selective retry, command-specific handling

3. **Different Configuration Needs:**
   - HTTP: Global settings for all requests
   - CQRS: Per-command configuration (some commands retryable, others not)

4. **Separation of Concerns:**
   - Infrastructure failures ≠ Business logic failures
   - HTTP middleware should not know about domain commands
   - Command handlers should not know about HTTP details

### Current Strategy

**Phase 1 (Current):** HTTP resilience only
- Sufficient for most scenarios
- Protects against infrastructure failures
- Simple to configure and monitor

**Phase 2 (Future):** Add CQRS resilience when needed
- Activate for specific critical commands
- Fine-tuned retry/circuit breaker per operation
- When domain-specific error handling required

## Consequences

### Positive

- **Clear Responsibility:** Each layer handles appropriate concerns
- **No Redundancy:** HTTP layer protects infrastructure, CQRS layer available for domain
- **Flexibility:** Can activate CQRS resilience per-command as needed
- **Performance:** Not running double circuit breakers unnecessarily
- **Monitoring:** Easier to track failures at correct layer

### Negative

- **Complexity:** Two systems to understand and maintain
- **Potential Confusion:** Developers might not know which to use
- **Code Duplication:** Similar patterns in both layers

### Neutral

- **Gradual Activation:** CQRS resilience activated only when metrics show need
- **Documentation Required:** Must clearly document when to use each layer

## Implementation Guidelines

### When to Use HTTP Layer Resilience

✅ **Always active** for:
- Database connection pooling issues
- External API calls (payment gateways, email services)
- Network timeouts
- Infrastructure dependencies (Redis, MinIO, Elasticsearch)
- Rate limiting from downstream services

### When to Activate CQRS Layer Resilience

Activate for specific commands when:
- Command has domain-specific transient failure modes
- Different commands need different retry strategies
- Command-level circuit breaking required (e.g., payment processing)
- Fine-grained control needed per operation

**Example: Payment Command**
```python
# Activate resilience for critical payment command
payment_resilience = ResilienceMiddleware(
    retry_config=RetryConfig(
        max_retries=2,  # Only 2 retries for payments
        base_delay=5.0,  # Longer delay between retries
        retryable_exceptions=(PaymentGatewayTimeout,)  # Specific exceptions
    ),
    circuit_config=CircuitBreakerConfig(
        failure_threshold=10,  # More tolerance for payments
        recovery_timeout=120.0  # Longer recovery period
    )
)
command_bus.add_middleware(payment_resilience)
```

### Configuration Best Practices

#### HTTP Layer (Global)
```python
# src/main.py
ResilienceConfig(
    failure_threshold=5,      # Conservative for all endpoints
    timeout_seconds=30.0,     # Global timeout
    enabled=True              # Always on
)
```

#### CQRS Layer (Per-Command)
```python
# src/infrastructure/di/cqrs_bootstrap.py
from application.common.middleware import ResilienceMiddleware, RetryConfig, CircuitBreakerConfig

async def bootstrap_cqrs_with_resilience(command_bus: CommandBus):
    # Only for specific critical commands
    if settings.enable_payment_resilience:
        payment_resilience = ResilienceMiddleware(
            retry_config=RetryConfig(max_retries=2),
            circuit_config=CircuitBreakerConfig(failure_threshold=10)
        )
        command_bus.add_middleware(payment_resilience)
```

## Monitoring and Observability

### HTTP Layer Metrics
```python
# Logged automatically by ResilienceMiddleware
{
    "layer": "http",
    "circuit_state": "OPEN",
    "failure_count": 5,
    "path": "/api/v1/users"
}
```

### CQRS Layer Metrics (when active)
```python
# Logged by CQRS ResilienceMiddleware
{
    "layer": "cqrs",
    "command_type": "ProcessPaymentCommand",
    "retry_attempt": 2,
    "circuit_state": "HALF_OPEN"
}
```

## Migration Path

### Phase 1 (Current - ✅ Complete)
- HTTP resilience active
- CQRS resilience available but inactive
- Monitor for domain-specific failure patterns

### Phase 2 (Future - When Needed)
- Identify commands needing specific resilience
- Activate CQRS middleware for those commands
- Monitor and tune per-command configurations

### Phase 3 (Advanced - Optional)
- Dynamic configuration per command type
- Adaptive circuit breakers based on SLI/SLO
- Machine learning for optimal retry strategies

## Testing Strategy

### HTTP Resilience Testing
```python
# tests/integration/middleware/test_http_resilience.py
async def test_circuit_breaker_opens_after_failures():
    # Simulate 5 failures
    for _ in range(5):
        await make_failing_request()

    # Next request should be rejected immediately
    response = await make_request()
    assert response.status_code == 503  # Service Unavailable
```

### CQRS Resilience Testing (when activated)
```python
# tests/unit/application/middleware/test_cqrs_resilience.py
async def test_command_retry_on_transient_error():
    resilience = ResilienceMiddleware(RetryConfig(max_retries=3))

    # Mock handler that fails twice then succeeds
    handler = Mock(side_effect=[
        ConnectionError(),
        ConnectionError(),
        Ok(result)
    ])

    result = await resilience(command, handler)
    assert result.is_ok()
    assert handler.call_count == 3
```

## Alternatives Considered

### Alternative 1: Single Resilience Layer

**Pros:**
- Simpler architecture
- Less code duplication
- Easier to understand

**Cons:**
- Mixing infrastructure and domain concerns
- One-size-fits-all configuration
- Cannot tune per-command

**Rejected because:** Different layers have different failure modes and recovery strategies.

### Alternative 2: CQRS Resilience Only

**Pros:**
- Fine-grained control
- Domain-centric

**Cons:**
- Doesn't protect infrastructure layer
- HTTP endpoints without commands unprotected
- More complex configuration

**Rejected because:** Infrastructure failures need protection before reaching application layer.

### Alternative 3: External Service Mesh

**Pros:**
- Centralized resilience management
- Language agnostic
- Advanced features (Istio, Linkerd)

**Cons:**
- Operational complexity
- Infrastructure dependency
- Overkill for monolith

**Deferred:** Consider when migrating to microservices.

## Related Decisions

- ADR-001: CQRS Pattern (command/query separation)
- ADR-004: Unit of Work Strategy (transaction boundaries)
- ADR-006: Observability Strategy (metrics and logging)

## Review Notes

- **Review date:** 2025-Q2 or when failure patterns emerge
- **Review trigger:** If >10% of commands need custom resilience
- **Consider:** Service mesh if moving to microservices

## References

- [Martin Fowler - Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Microsoft - Retry Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Release It! by Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [Resilience4j Documentation](https://resilience4j.readme.io/)
