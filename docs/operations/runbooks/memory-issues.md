# Runbook: Memory Issues

## Metadata

- **Severity:** P1
- **SLO Impact:** Service availability, potential OOM kills
- **Recovery Time Estimate:** 10-30 minutes
- **Last Updated:** December 2025
- **Owner:** Platform Team

## Symptoms

- OOMKilled pods
- High memory usage alerts
- Slow response times
- Pod restarts

## Diagnosis

### Step 1: Check Pod Memory Usage

```bash
# Check current memory usage
kubectl top pods -l app=api

# Check for OOMKilled
kubectl get pods -l app=api -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'
```

**Expected:** Memory < 80% of limit

### Step 2: Check Memory Trends

```bash
# Query Prometheus for memory trend
curl -s "http://prometheus:9090/api/v1/query_range?query=container_memory_usage_bytes{container='api'}&start=$(date -d '1 hour ago' +%s)&end=$(date +%s)&step=60"
```

### Step 3: Check for Memory Leaks

```bash
# Get memory profile
kubectl exec -it api-pod -- python -c "
import tracemalloc
tracemalloc.start()
# ... run some operations ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
"
```

### Step 4: Check Database Connections

```bash
# Check connection pool
kubectl exec -it api-pod -- python -c "
from infrastructure.db import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked out: {engine.pool.checkedout()}')
"
```

## Resolution

### Option A: Restart Pods (Immediate Relief)

```bash
# Rolling restart
kubectl rollout restart deployment api

# Verify
kubectl rollout status deployment api
```

### Option B: Increase Memory Limits

```bash
# Update deployment
kubectl patch deployment api -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

### Option C: Fix Memory Leak

If leak identified:

1. Identify leaking code
2. Fix and deploy

Common causes:
- Unclosed database connections
- Large objects in memory
- Circular references

```python
# Example fix: ensure connections are closed
async with session.begin():
    # ... operations ...
    pass  # Connection closed automatically
```

### Option D: Scale Horizontally

```bash
# Add more pods to distribute load
kubectl scale deployment api --replicas=5
```

## Verification

```bash
# Check memory usage
kubectl top pods -l app=api

# Should be < 80% of limit

# Check no OOMKilled
kubectl get pods -l app=api
```

## Escalation

- **Level 1:** On-call engineer (immediate)
- **Level 2:** Platform team lead (15 min)
- **Level 3:** Engineering manager (30 min)

## Post-Incident

- [ ] Analyze memory dump
- [ ] Fix memory leak if found
- [ ] Update memory limits
- [ ] Add memory alerts
