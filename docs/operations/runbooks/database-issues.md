# Runbook: Database Connection Issues

## Metadata

- **Severity:** P1 (Critical)
- **SLO Impact:** API availability and response time SLOs affected
- **Recovery Time Estimate:** 5-30 minutes
- **Last Updated:** 2025-01-15
- **Owner:** Platform Team

## Overview

This runbook addresses database connection problems including connection pool exhaustion, timeouts, and connectivity failures.

## Symptoms

- API returning 500 errors with database-related messages
- Slow response times
- Connection timeout errors in logs
- "Too many connections" errors
- Health check `/health/ready` failing

## Impact

- API requests failing
- Data operations unavailable
- Potential data inconsistency if mid-transaction

## Prerequisites

- Access to application logs
- Database admin credentials
- kubectl access (if K8s)
- PostgreSQL client tools

## Diagnosis

### Step 1: Check Application Logs

```bash
# Kubernetes
kubectl logs -l app=python-api-base --tail=100 | grep -i "database\|connection\|pool"

# Docker
docker logs python-api-base 2>&1 | grep -i "database\|connection\|pool"
```

**Look for:**
- `connection pool exhausted`
- `connection timeout`
- `too many connections`
- `connection refused`

### Step 2: Check Database Status

```bash
# Connect to PostgreSQL
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Check active connections
SELECT count(*) FROM pg_stat_activity;

# Check connections by state
SELECT state, count(*) 
FROM pg_stat_activity 
GROUP BY state;

# Check connections by application
SELECT application_name, count(*) 
FROM pg_stat_activity 
GROUP BY application_name;
```

**Expected:** Active connections < max_connections (typically 100)

### Step 3: Check Connection Pool Metrics

```bash
# If Prometheus metrics available
curl http://localhost:8000/metrics | grep db_pool
```

**Metrics to check:**
- `db_pool_size` - Current pool size
- `db_pool_checkedout` - Connections in use
- `db_pool_overflow` - Overflow connections

### Step 4: Check Network Connectivity

```bash
# From application pod/container
nc -zv $DB_HOST 5432

# DNS resolution
nslookup $DB_HOST
```

## Resolution

### Option A: Connection Pool Exhaustion

**When to use:** Pool metrics show all connections in use

1. **Immediate: Restart application pods**
   ```bash
   kubectl rollout restart deployment/python-api-base
   ```

2. **Increase pool size** (if resources allow)
   ```bash
   # Update environment variable
   DATABASE__POOL_SIZE=20
   DATABASE__MAX_OVERFLOW=30
   ```

3. **Investigate slow queries**
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY duration DESC;
   ```

### Option B: Database Unreachable

**When to use:** Network connectivity fails

1. **Check database service status**
   ```bash
   # Kubernetes
   kubectl get pods -l app=postgresql
   kubectl describe pod postgresql-0
   
   # Check service
   kubectl get svc postgresql
   ```

2. **Check database logs**
   ```bash
   kubectl logs postgresql-0 --tail=100
   ```

3. **Restart database if needed**
   ```bash
   kubectl rollout restart statefulset/postgresql
   ```

### Option C: Too Many Connections

**When to use:** Database reports max connections reached

1. **Terminate idle connections**
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
   AND query_start < now() - interval '10 minutes';
   ```

2. **Increase max_connections** (requires restart)
   ```sql
   ALTER SYSTEM SET max_connections = 200;
   ```

3. **Consider connection pooler** (PgBouncer)

### Option D: Slow Queries

**When to use:** Connections held by long-running queries

1. **Identify slow queries**
   ```sql
   SELECT pid, query, now() - query_start AS duration
   FROM pg_stat_activity
   WHERE state = 'active'
   AND now() - query_start > interval '30 seconds';
   ```

2. **Cancel problematic queries**
   ```sql
   SELECT pg_cancel_backend(pid);
   -- Or force terminate
   SELECT pg_terminate_backend(pid);
   ```

3. **Add missing indexes**
   ```sql
   EXPLAIN ANALYZE <slow_query>;
   ```

## Verification

After resolution:

```bash
# Check health endpoint
curl http://localhost:8000/health/ready

# Check application logs for errors
kubectl logs -l app=python-api-base --tail=50 | grep -i error

# Verify database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

## Escalation

If issue persists after 30 minutes:

1. Contact: Database Team
2. Slack: #database-oncall
3. PagerDuty: Database Service

## Post-Incident

- [ ] Document root cause
- [ ] Review connection pool settings
- [ ] Add/update monitoring alerts
- [ ] Schedule capacity review if needed
- [ ] Update runbook if new scenarios found

## Prevention

1. **Monitoring:**
   - Alert on pool utilization > 80%
   - Alert on connection count > 80% of max
   - Alert on query duration > 30s

2. **Configuration:**
   - Set appropriate pool size for workload
   - Configure connection timeouts
   - Enable connection health checks

3. **Code:**
   - Use async context managers for sessions
   - Avoid long-running transactions
   - Implement query timeouts

## Related

- Cache Failures: See runbooks directory
- High Latency: See runbooks directory
- [Database Configuration](../../layers/infrastructure/database.md)
