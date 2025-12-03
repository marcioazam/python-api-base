# Runbook: High Latency

## Metadata

- **Severity:** P2
- **SLO Impact:** Response time SLO breach (p99 > 500ms)
- **Recovery Time Estimate:** 15-60 minutes
- **Last Updated:** December 2025
- **Owner:** Platform Team

## Symptoms

- API response times > 500ms (p99)
- Increased timeout errors
- User complaints about slow responses
- Grafana alerts for latency

## Diagnosis

### Step 1: Check Current Latency

```bash
# Check Prometheus metrics
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,rate(http_request_duration_seconds_bucket[5m]))"
```

**Expected:** p99 < 500ms

### Step 2: Identify Slow Endpoints

```bash
# Query for slowest endpoints
curl -s "http://prometheus:9090/api/v1/query?query=topk(10,histogram_quantile(0.99,rate(http_request_duration_seconds_bucket[5m]))by(endpoint))"
```

### Step 3: Check Database Performance

```bash
# Check slow queries
kubectl exec -it postgres-0 -- psql -U postgres -c "
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

**Expected:** No queries > 100ms mean time

### Step 4: Check Redis Performance

```bash
# Check Redis latency
kubectl exec -it redis-0 -- redis-cli --latency-history
```

**Expected:** Latency < 1ms

### Step 5: Check External Services

```bash
# Check circuit breaker states
curl http://api:8000/health/ready | jq '.checks'
```

## Resolution

### Option A: Database Optimization

If slow queries identified:

1. Add missing indexes
2. Optimize query
3. Increase connection pool

```bash
# Add index
kubectl exec -it postgres-0 -- psql -U postgres -c "
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
"
```

### Option B: Cache Warming

If cache miss rate high:

1. Identify frequently accessed data
2. Pre-warm cache

```bash
# Warm cache
kubectl exec -it api-pod -- python -c "
from infrastructure.cache import warm_cache
import asyncio
asyncio.run(warm_cache())
"
```

### Option C: Scale Horizontally

If CPU/memory high:

```bash
# Scale API pods
kubectl scale deployment api --replicas=5

# Verify
kubectl get pods -l app=api
```

### Option D: Rate Limit Aggressive Clients

```bash
# Check top clients
kubectl logs -l app=api | jq -r '.client_ip' | sort | uniq -c | sort -rn | head

# Add rate limit rule
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: rate-limits
data:
  aggressive-client: "10.0.0.1:10/minute"
EOF
```

## Verification

```bash
# Check latency improved
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,rate(http_request_duration_seconds_bucket[5m]))"

# Should be < 500ms
```

## Escalation

- **Level 1:** On-call engineer (15 min)
- **Level 2:** Platform team lead (30 min)
- **Level 3:** Engineering manager (1 hour)

## Post-Incident

- [ ] Update slow query monitoring
- [ ] Add missing indexes
- [ ] Review caching strategy
- [ ] Update capacity planning
