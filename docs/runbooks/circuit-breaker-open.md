# Circuit Breaker Open

## Severity
Medium

## Symptoms

- API returning 503 for specific operations
- Logs showing `CircuitOpenError`
- Metrics showing circuit breaker in OPEN state
- External service calls failing fast
- Error messages: "Circuit breaker is open"

## Impact

- Operations depending on external service unavailable
- Fast failure (good for system protection)
- Users see errors for affected features
- Potential cascade prevention (positive)

## Prerequisites

- Access to application logs
- Access to metrics endpoint
- Understanding of which services have circuit breakers
- Access to external service status

## Diagnosis Steps

### 1. Identify Which Circuit Breaker is Open

```bash
# Check logs for circuit breaker events
kubectl logs -l app=python-api-base --tail=200 | grep -i "circuit"

# Check metrics
curl http://localhost:8000/metrics | grep circuit_breaker
```

Look for:
- `circuit_breaker_state{service="<name>"} 1` (1 = OPEN)
- `circuit_breaker_failures_total`

### 2. Check External Service Status

```bash
# Direct connectivity test
curl -v <external-service-url>/health

# From application pod
kubectl exec -it <pod-name> -- curl <external-service-url>/health
```

### 3. Review Failure History

```bash
# Check recent errors
kubectl logs -l app=python-api-base --since=30m | grep -i "error\|fail" | grep <service-name>
```

### 4. Check Circuit Breaker Configuration

```python
# Review configuration in code
# src/infrastructure/resilience/patterns.py
CircuitBreakerConfig(
    failure_threshold=5,    # Failures to open
    success_threshold=3,    # Successes to close
    timeout=30.0,           # Seconds before half-open
)
```

## Resolution Steps

### Scenario 1: External Service is Down

**Symptoms**: External service not responding

**Resolution**:

1. Confirm external service status:
```bash
curl -v <external-service-url>/health
```

2. Check external service status page (if available)

3. Wait for external service recovery

4. Circuit breaker will automatically transition to HALF_OPEN after timeout

5. If urgent, consider:
   - Enabling fallback behavior
   - Disabling the feature temporarily
   - Using cached data if available

### Scenario 2: Network Issues

**Symptoms**: Intermittent connectivity

**Resolution**:

1. Check network connectivity:
```bash
kubectl exec -it <pod-name> -- ping <external-host>
kubectl exec -it <pod-name> -- traceroute <external-host>
```

2. Check DNS resolution:
```bash
kubectl exec -it <pod-name> -- nslookup <external-host>
```

3. Check firewall/security groups

4. If network is fixed, wait for circuit to reset

### Scenario 3: External Service Overloaded

**Symptoms**: Service responding slowly or with errors

**Resolution**:

1. Check external service response times:
```bash
time curl <external-service-url>/api/endpoint
```

2. Reduce request rate if possible

3. Contact external service team

4. Consider implementing rate limiting on your side

### Scenario 4: Configuration Issue

**Symptoms**: Circuit opening too easily

**Resolution**:

1. Review circuit breaker configuration:
```python
# Increase failure threshold if too sensitive
CircuitBreakerConfig(
    failure_threshold=10,  # Was 5
    success_threshold=3,
    timeout=60.0,          # Was 30
)
```

2. Review which exceptions trigger the circuit:
```python
# Exclude expected exceptions
excluded_exceptions=(ValidationError, NotFoundError)
```

3. Deploy configuration change

### Manual Circuit Reset (Emergency Only)

If you need to force reset the circuit breaker:

```python
# This requires code access or admin endpoint
# Add admin endpoint for circuit management
@router.post("/admin/circuit-breaker/{service}/reset")
async def reset_circuit(service: str):
    circuit_breakers[service].reset()
    return {"status": "reset"}
```

```bash
curl -X POST http://localhost:8000/admin/circuit-breaker/<service>/reset
```

## Verification

1. Check circuit breaker state:
```bash
curl http://localhost:8000/metrics | grep circuit_breaker_state
```

2. Test affected endpoint:
```bash
curl http://localhost:8000/api/v1/<affected-endpoint>
```

3. Monitor for successful requests:
```bash
kubectl logs -f -l app=python-api-base | grep <service-name>
```

4. Verify external service is healthy:
```bash
curl <external-service-url>/health
```

## Prevention

1. **Proper Configuration**:
   - Set appropriate failure thresholds
   - Configure reasonable timeouts
   - Exclude expected exceptions

2. **Fallback Strategies**:
   - Implement fallback responses
   - Use cached data when possible
   - Provide degraded functionality

3. **Monitoring**:
   - Alert on circuit breaker state changes
   - Monitor failure rates
   - Track external service health

4. **Testing**:
   - Test circuit breaker behavior
   - Simulate external service failures
   - Verify fallback behavior

5. **Documentation**:
   - Document which services have circuit breakers
   - Document expected behavior when open
   - Document manual intervention procedures

## Circuit Breaker States

```
CLOSED (Normal)
    │
    │ failure_threshold reached
    ▼
  OPEN (Failing Fast)
    │
    │ timeout elapsed
    ▼
HALF_OPEN (Testing)
    │
    ├── success_threshold reached → CLOSED
    │
    └── failure → OPEN
```

## Related

- [ADR-009: Resilience Patterns](../adr/ADR-009-resilience-patterns.md)
- [Patterns Guide](../patterns.md#4-resilience-patterns)
- [Monitoring Guide](../monitoring.md)
